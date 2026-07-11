"""Tests for the ingestion layer (stage 1: PDF -> RawSection).

Two tiers:
  - Pure-function tests for verify_section_counts (the delta gate). No I/O, always run,
    CI-safe.
  - Integration tests that parse the real BNS/BNSS/BSA PDFs in data/raw/. These skip
    cleanly when the PDFs aren't present (they're git-ignored, licensing), so CI stays
    green without them, but they're the real proof the parser hits the published counts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.ingest.parse_pdf import (
    PUBLISHED_SECTION_COUNTS,
    RawSection,
    parse_statute,
    verify_section_counts,
)

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
PDFS = {"BNS": RAW / "bns.pdf", "BNSS": RAW / "bnss.pdf", "BSA": RAW / "bsa.pdf"}


class TestVerifySectionCounts:
    """The count gate is pure and deterministic, so it gets the hardest tests."""

    def test_reports_signed_delta(self) -> None:
        secs = [RawSection("BSA", str(i), "h", "body") for i in range(1, 169)]  # 168
        assert verify_section_counts(secs, {"BSA": 170}) == {"BSA": -2}


def _require(act: str) -> Path:
    path = PDFS[act]
    if not path.exists():
        pytest.skip(f"{path} not present (git-ignored source PDF); drop it in to run")
    return path


@pytest.mark.parametrize("act", ["BNS", "BNSS", "BSA"])
class TestParseRealStatutes:
    def test_section_count_matches_published_total(self, act: str) -> None:
        secs = parse_statute(_require(act), act)
        assert len(secs) == PUBLISHED_SECTION_COUNTS[act]

    def test_no_section_body_leaks_into_next(self, act: str) -> None:
        """A body shouldn't contain the next section's numbered dash-heading start."""
        import re

        secs = parse_statute(_require(act), act)
        leak = re.compile(r"(?m)^\s*\d+[A-Z]?\.\s+\w.{0,60}(?:—|–|--)")
        offenders = [s.section_id for s in secs if leak.search(s.text)]
        assert offenders == []


class TestKnownContent:
    """Spot-check that famous sections parse with the right heading + body."""

    def test_last_section_stops_before_schedule(self) -> None:
        """BNSS s.531 must not swallow the trailing schedule of forms (was 197KB)."""
        secs = parse_statute(_require("BNSS"), "BNSS")
        last = next(s for s in secs if s.section_id == "531")
        assert "Seal of the Court" not in last.text
        assert len(last.text) < 20_000

    def test_bns_definitions_continue_past_pdf_footnote(self) -> None:
        secs = parse_statute(_require("BNS"), "BNS")
        definitions = next(s for s in secs if s.section_id == "2")
        assert "valuable security" in definitions.text
        assert "legal right is created, extended, transferred" in definitions.text
