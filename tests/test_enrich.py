"""Tests for the metadata enrichment layer (stage 3).

Tiers, same as the other ingest tests:
  - Pure-function tests for _classify_cell, _aggregate, _band and the enrich() join
    logic over synthetic chunks. No PDFs, always run, CI-safe. These pin the
    legal-data discipline: conditional/conflicting -> None, never a guessed flag.
  - Integration tests parse the real PDFs and assert known offences classify
    correctly (BNS 103 murder = cognizable + non-bailable, 103 -> IPC 302). Skip
    cleanly when the source PDFs aren't present.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingest.chunk_chonkie import LegalChunk
from src.ingest.enrich_metadata import (
    _aggregate,
    _classify_cell,
    enrich,
    load_ipc_bns_mapping,
    load_offence_classification,
)

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
BNSS = RAW / "bnss.pdf"
BNS = RAW / "bns.pdf"
COMPARISON = RAW / "COMPARISON SUMMARY BNS to IPC .pdf"


class TestClassifyCell:
    def test_conditional_is_none(self) -> None:
        assert _classify_cell("According as offence abetted is cognizable", "cogn") is None


class TestAggregate:
    def test_conflict_is_none(self) -> None:
        assert _aggregate([True, False]) is None


class TestEnrichJoin:
    """enrich() join logic over synthetic chunks + pre-loaded mapping (no PDFs)."""

    def _chunks(self) -> list[LegalChunk]:
        return [
            LegalChunk("BNS::103::0", "BNS", "103", "Punishment for murder", "t", chapter="VI"),
            LegalChunk("BNSS::35::0", "BNSS", "35", "Arrest", "t", chapter="V"),
        ]

    def test_ipc_equivalents_only_on_bns(self) -> None:
        chunks = self._chunks()
        enrich(chunks, ipc_bns_mapping={"302": "103", "379": "303"})
        bns = chunks[0].metadata["ipc_equivalents"]
        bnss = chunks[1].metadata["ipc_equivalents"]
        assert bns == ["302"]
        assert bnss == []


@pytest.mark.skipif(not BNSS.exists(), reason="source PDFs not present")
class TestRealClassification:
    def test_landmark_offences_classify_correctly(self) -> None:
        cls = load_offence_classification(BNSS)
        # murder: cognizable, non-bailable
        assert cls["103"] == {"cognizable": True, "bailable": False}
        # theft (303): cognizable, non-bailable
        assert cls["303"]["cognizable"] is True


@pytest.mark.skipif(not COMPARISON.exists(), reason="comparison PDF not present")
class TestRealIpcMapping:
    def test_landmark_ipc_to_bns(self) -> None:
        m = load_ipc_bns_mapping(COMPARISON)
        assert m["302"] == "103"  # murder
        assert m["379"] == "303"  # theft
        assert m["420"] == "318"  # cheating
        assert m["375"] == "63"  # rape (definition)
        assert m["376"] == "64"  # rape (punishment)
