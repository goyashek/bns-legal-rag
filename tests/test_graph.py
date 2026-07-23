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

from langgraph.graph import END

from src.agent.graph import (
    CITATION_REPAIR_BUDGET,
    RETRIEVAL_LOOP_BUDGET,
    _complete_repeated_sections,
    _dedupe_by_chunk_id,
    build_graph,
    retrieve_node,
    route_after_citation_validator,
    route_after_fast_path,
    route_after_production_citation_validator,
)
from src.ingest.chunk_chonkie import LegalChunk
from src.retrieval.hybrid import RetrievedChunk

_INDEX = Path("data/processed/sections.jsonl")
_QDRANT = Path("data/processed/qdrant")
_have_index = _INDEX.exists()
_have_full_index = _INDEX.exists() and _QDRANT.exists() and Path("data/processed/bm25.pkl").exists()


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

    def retrieve(
        self, query: str, *, top_k: int = 20, mode: str = "hybrid"
    ) -> list[RetrievedChunk]:
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
            route_after_citation_validator({"citation_valid": False, "iteration": 0}) == "rewriter"
        )

    def test_invalid_citations_budget_spent_low_confidence(self) -> None:
        assert (
            route_after_citation_validator(
                {"citation_valid": False, "iteration": RETRIEVAL_LOOP_BUDGET}
            )
            == "low_confidence"
        )

    def test_production_repairs_an_invalid_citation_once(self) -> None:
        assert route_after_production_citation_validator({"citation_valid": True}) == END
        assert (
            route_after_production_citation_validator({"citation_valid": False, "iteration": 0})
            == "citation_repair"
        )
        assert (
            route_after_production_citation_validator(
                {"citation_valid": False, "iteration": CITATION_REPAIR_BUDGET}
            )
            == "low_confidence"
        )


class TestRetrieveNode:
    """Fan over sub-queries + dedupe, using fakes (no models, no key)."""

    def test_dedupe_keeps_best_rrf(self) -> None:
        dupes = [_rc("BNS::103::0", 0.2), _rc("BNS::103::0", 0.9), _rc("BNS::63::0", 0.5)]
        out = {c.chunk.chunk_id: c.rrf_score for c in _dedupe_by_chunk_id(dupes)}
        assert out == {"BNS::103::0": 0.9, "BNS::63::0": 0.5}

    def test_repeated_section_gets_missing_sibling(self) -> None:
        ranked = [_rc("BNS::314::1", 0.9), _rc("BNS::314::2", 0.8)]
        corpus = [_rc(f"BNS::314::{i}", 0).chunk for i in range(3)]
        out = _complete_repeated_sections(ranked, corpus)
        assert [c.chunk.chunk_id for c in out] == [
            "BNS::314::1",
            "BNS::314::2",
            "BNS::314::0",
        ]

    def test_dense_mode_keeps_twelve_chunks_for_generation(self) -> None:
        chunks = [_rc(f"BNS::{section}::0", 1.0 - section / 1000) for section in range(100, 113)]
        retr = _FakeRetriever({"query": chunks})
        out = retrieve_node({"query": "query"}, retriever=retr, mode="dense", use_reranker=False)
        assert [c.chunk.section_id for c in out["retrieved"]] == [str(s) for s in range(100, 112)]


class TestGraphCompiles:
    def test_build_graph_returns_compiled(self) -> None:
        g = build_graph()
        assert hasattr(g, "invoke")
