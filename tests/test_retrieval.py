"""Tests for the retrieval layer.

Two tiers, same pattern as the ingest tests:
  - Pure-function tests (RRF math, tokenizer, deterministic point ids) run always,
    no models, no index, CI-safe. RRF is the deterministic core so it gets the
    hardest tests.
  - Integration tests build against the real Qdrant + BM25 indices and the bge
    models; they skip cleanly when the indices aren't present (they're git-ignored,
    regenerated from source).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.retrieval.hybrid import reciprocal_rank_fusion
from src.retrieval.index import tokenize

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
QDRANT_DIR = PROCESSED / "qdrant"
BM25_PKL = PROCESSED / "bm25.pkl"


class TestReciprocalRankFusion:
    def test_score_uses_k_smoothing(self) -> None:
        """RRF score for rank-0 in both lists == 2/k with k=60 (rank is 0-based)."""
        fused = dict(reciprocal_rank_fusion(["a"], ["a"], k=60))
        assert fused["a"] == pytest.approx(2 / 60)

    def test_ties_broken_deterministically_by_id(self) -> None:
        """Two chunks with equal score come back in stable (id-sorted) order."""
        fused = reciprocal_rank_fusion(["x"], ["y"], k=60)  # both score 1/60
        assert [cid for cid, _ in fused] == ["x", "y"]


class TestTokenize:
    def test_lowercases_and_splits_alnum(self) -> None:
        assert tokenize("BNS Section 103: Murder!") == ["bns", "section", "103", "murder"]


@pytest.mark.skipif(
    not (QDRANT_DIR.exists() and BM25_PKL.exists()),
    reason="retrieval indices not built; run src/retrieval/index.py",
)
class TestHybridRetrieverIntegration:
    """End-to-end retrieval against the real indices + bge models.

    These are the real proof the plumbing works: a plain-language query about a crime
    should surface the right BNS section near the top.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def retriever(cls):
        from src.retrieval.hybrid import HybridRetriever

        r = HybridRetriever(collection="legal", bm25_path=str(BM25_PKL))
        yield r
        r.client.close()

    def test_murder_query_surfaces_section_103(self, retriever) -> None:
        results = retriever.retrieve("what is the punishment for murder", top_k=10)
        section_ids = {r.chunk.section_id for r in results if r.chunk.act == "BNS"}
        assert "103" in section_ids

    @pytest.mark.parametrize("mode", ["dense", "sparse"])
    def test_single_signal_modes_return_ranked_chunks(self, retriever, mode: str) -> None:
        results = retriever.retrieve("what is the punishment for murder", top_k=5, mode=mode)

        assert 1 <= len(results) <= 5
        if mode == "dense":
            assert all(r.dense_rank is not None and r.sparse_rank is None for r in results)
        else:
            assert all(r.sparse_rank is not None and r.dense_rank is None for r in results)


@pytest.mark.skipif(
    not (QDRANT_DIR.exists() and BM25_PKL.exists()),
    reason="retrieval indices not built",
)
class TestRerankerIntegration:
    def test_rerank_reorders_and_caps(self) -> None:
        from src.retrieval.hybrid import HybridRetriever
        from src.retrieval.rerank import Reranker

        retriever = HybridRetriever(collection="legal", bm25_path=str(BM25_PKL))
        try:
            candidates = retriever.retrieve("punishment for murder", top_k=20)
            reranked = Reranker().rerank("punishment for murder", candidates, top_k=8)

            assert len(reranked) <= 8
            assert all(r.rerank_score is not None for r in reranked)
            # sorted by rerank score desc
            scores = [r.rerank_score for r in reranked]
            assert scores == sorted(scores, reverse=True)
        finally:
            retriever.client.close()
