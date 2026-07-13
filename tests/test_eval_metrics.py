"""Tests for the section-precision metrics (src/eval/section_precision.py).

All pure set/list ops over section-id labels, no LLM, no index. These pin the edge
cases that bite when computing a baseline: dedup in P@k, the < k retrieved case, and
the vacuous-truth conventions (empty relevant -> recall 1.0, empty cited -> accuracy
1.0).
"""

from __future__ import annotations

from src.eval.section_precision import (
    citation_accuracy,
    section_precision_at_k,
    section_recall,
)


class TestPrecisionAtK:
    def test_half_relevant(self) -> None:
        assert section_precision_at_k(["a", "x", "b", "y"], ["a", "b"], k=4) == 0.5


class TestRecall:
    def test_partial(self) -> None:
        assert section_recall(["a", "x"], ["a", "b"]) == 0.5


class TestCitationAccuracy:
    def test_one_wrong(self) -> None:
        assert citation_accuracy(["a", "z"], ["a", "b"]) == 0.5
