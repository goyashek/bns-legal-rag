"""Tests for the graph wiring.

Layers:
  - routing functions: pure, branch on state, no key/index (the bulk here).
  - retrieve_node fan/dedupe: fake retriever + reranker, no models, no key.
  - fast-path e2e: keyless — a "BNS 103" query hits the deterministic fast path
    and ends without any LLM call, exercising the real StateGraph. Needs the
    built index (data/processed/sections.jsonl), so it skips when that's absent.
  - criminal-branch e2e: live DeepSeek (router + expander) + real retrieval; gated
    on both the key and the index.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.graph import END

from src.agent.graph import (
    RETRIEVAL_LOOP_BUDGET,
    _dedupe_by_chunk_id,
    answer_query,
    build_graph,
    retrieve_node,
    route_after_checker,
    route_after_citation_validator,
    route_after_fast_path,
    route_after_grader,
    route_after_ood_gate,
    route_after_router,
)
from src.agent.llm import has_api_key
from src.agent.nodes.citation_validator import validate_citations
from src.ingest.chunk_chonkie import LegalChunk
from src.retrieval.hybrid import RetrievedChunk

_INDEX = Path("data/processed/sections.jsonl")
_QDRANT = Path("data/processed/qdrant")
_have_index = _INDEX.exists()
_have_full_index = (
    _INDEX.exists() and _QDRANT.exists() and Path("data/processed/bm25.pkl").exists()
)


def _rc(chunk_id: str, rrf: float) -> RetrievedChunk:
    section = chunk_id.split("::")[1]
    return RetrievedChunk(
        chunk=LegalChunk(chunk_id, "BNS", section, "heading", "text"), rrf_score=rrf
    )


class _FakeRetriever:
    """Returns a canned hit list keyed by query; records calls."""

    def __init__(self, per_query: dict[str, list[RetrievedChunk]]) -> None:
        self._per_query = per_query
        self.calls: list[str] = []

    def retrieve(self, query: str, *, top_k: int = 20) -> list[RetrievedChunk]:
        self.calls.append(query)
        return self._per_query.get(query, [])


class _PassThroughReranker:
    """Reranker stand-in: returns the first top_k unchanged; records the query."""

    def __init__(self) -> None:
        self.query: str | None = None

    def rerank(self, query, candidates, *, top_k=8):  # noqa: ANN001
        self.query = query
        return candidates[:top_k]


class TestRoutingFunctions:
    def test_fast_path_hit_goes_to_end(self) -> None:
        assert route_after_fast_path({"fast_path_hit": True}) == END

    def test_invalid_citations_rewrite_within_budget(self) -> None:
        assert (
            route_after_citation_validator({"citation_valid": False, "iteration": 0})
            == "rewriter"
        )

    def test_invalid_citations_budget_spent_low_confidence(self) -> None:
        assert (
            route_after_citation_validator(
                {"citation_valid": False, "iteration": RETRIEVAL_LOOP_BUDGET}
            )
            == "low_confidence"
        )


class TestRetrieveNode:
    """Fan over sub-queries + dedupe, using fakes (no models, no key)."""

    def test_dedupe_keeps_best_rrf(self) -> None:
        dupes = [
            _rc("BNS::103::0", 0.2),
            _rc("BNS::103::0", 0.9),
            _rc("BNS::63::0", 0.5),
        ]
        out = {c.chunk.chunk_id: c.rrf_score for c in _dedupe_by_chunk_id(dupes)}
        assert out == {"BNS::103::0": 0.9, "BNS::63::0": 0.5}


class TestGraphCompiles:
    def test_build_graph_returns_compiled(self) -> None:
        g = build_graph()
        assert hasattr(g, "invoke")
