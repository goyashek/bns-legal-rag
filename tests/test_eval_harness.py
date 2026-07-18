"""Tests for the RAGAS + MCQ harness plumbing (src/eval/ragas_eval.py, mcq_eval.py).

All keyless: agent runs, retrieval, ragas, and the gated dataset are injected as fakes,
so this pins the pure logic — reference building, sample extraction, RPM pacing, metric
aggregation (incl. NaN-skip), MCQ index clamping, and the honest bridge breakdown —
without a key, an index, or ragas installed. The live scoring itself runs out-of-band.
"""

from __future__ import annotations

import json

import pytest

from src.eval import mcq_eval, ragas_eval


# --- fakes -------------------------------------------------------------------
class _FakeChunk:
    def __init__(self, act: str, section_id: str, text: str = "", heading: str = "") -> None:
        self.act = act
        self.section_id = section_id
        self.text = text
        self.heading = heading


class _FakeRetrieved:
    def __init__(self, act: str, section_id: str, text: str = "", heading: str = "") -> None:
        self.chunk = _FakeChunk(act, section_id, text, heading)


class _FakeAnswer:
    def __init__(self, answer: str) -> None:
        self.answer = answer


class _FakeCitation:
    def model_dump(self, *, exclude_none: bool) -> dict[str, str]:
        assert exclude_none is True
        return {"act": "BNS", "section_id": "103"}


class _DetailedFakeAnswer(_FakeAnswer):
    citations = [_FakeCitation()]
    confidence = "high"
    in_corpus = True


# =============================== RAGAS =======================================
class TestBuildReference:
    def test_joins_gold_section_texts(self) -> None:
        tbs = {"BNS::103": ["murder punishment text"], "BNS::101": ["murder def"]}
        ref = ragas_eval.build_reference(["BNS::101", "BNS::103"], tbs)
        assert "murder def" in ref and "murder punishment text" in ref


class TestAggregate:
    def test_means_and_per_difficulty(self) -> None:
        rows = [
            {
                "faithfulness": 1.0,
                "answer_relevancy": 1.0,
                "context_precision": 1.0,
                "context_recall": 1.0,
                "difficulty": "easy",
            },
            {
                "faithfulness": 0.0,
                "answer_relevancy": 0.0,
                "context_precision": 0.0,
                "context_recall": 0.0,
                "difficulty": "hard",
            },
        ]
        s = ragas_eval.aggregate(rows)
        assert s.faithfulness == 0.5 and s.n_scenarios == 2
        assert s.per_difficulty["easy"]["faithfulness"] == 1.0
        assert s.per_difficulty["hard"]["faithfulness"] == 0.0

    def test_nan_is_skipped_not_counted_as_zero(self) -> None:
        nan = float("nan")
        rows = [
            {
                "faithfulness": 1.0,
                "answer_relevancy": 1.0,
                "context_precision": 1.0,
                "context_recall": 1.0,
                "difficulty": "easy",
            },
            {
                "faithfulness": nan,
                "answer_relevancy": nan,
                "context_precision": nan,
                "context_recall": nan,
                "difficulty": "easy",
            },
        ]
        # NaN dropped -> mean over the one real value = 1.0, not 0.5
        assert ragas_eval.aggregate(rows).faithfulness == 1.0


class TestRagasWorkers:
    def test_defaults_to_two_and_rejects_zero(self, monkeypatch) -> None:
        monkeypatch.delenv("RAGAS_MAX_WORKERS", raising=False)
        assert ragas_eval._ragas_max_workers() == 2
        monkeypatch.setenv("RAGAS_MAX_WORKERS", "0")
        with pytest.raises(ValueError, match="must be positive"):
            ragas_eval._ragas_max_workers()


# ============================ MCQ (BhashaBench) ==============================


class TestAnswerMcq:
    def test_clamps_out_of_range_index(self) -> None:
        class _FakeClient:
            def create(self, **_):
                return mcq_eval._MCQChoice(answer_idx=99)  # model hallucinates OOB

        idx = mcq_eval.answer_mcq(
            "q",
            ["a", "b", "c"],
            retriever=_FakeRetriever(),
            client=_FakeClient(),
        )
        assert idx == 2  # clamped to last valid


class _FakeRetriever:
    def retrieve(self, query: str, *, top_k: int = 20, mode: str = "hybrid"):
        return [_FakeRetrieved("BNS", "103", "murder text", "Punishment for murder")]


class TestComputeResult:
    def _slice(self):
        return [
            {"question": "q1", "options": ["a", "b"], "answer_idx": 0, "ipc_refs": ["302"]},
            {"question": "q2", "options": ["a", "b"], "answer_idx": 1, "ipc_refs": ["999"]},
            {"question": "q3", "options": ["a", "b"], "answer_idx": 0, "ipc_refs": []},
        ]

    def test_overall_and_bridge_subset(self) -> None:
        # 302 maps -> bridge-dependent; 999 unmapped; [] none. Only q1 is on the bridge.
        mapping = {"302": "103"}
        preds = [0, 0, 0]  # q1 right, q2 wrong, q3 right -> 2/3 overall
        res = mcq_eval.compute_result(self._slice(), preds, mapping)
        assert res.total == 3 and res.correct == 2
        assert abs(res.accuracy - 2 / 3) < 1e-9
        assert res.bridge_resolved == 1  # only q1
        assert res.bridge_accuracy == 1.0  # q1 predicted correctly
        assert res.baseline_accuracy is None
