"""Tests for the deterministic agent nodes.

These are the part I care most about, so they get the sharpest tests:
detect_exact_section (fires on "BNS 103", not on narratives) and is_out_of_domain
(threshold boundary both ways). Both are pure, no LLM, no index — CI-safe.

validate_citations (the correctness check) lands Week 2 Fri; its tests live here too
once that node exists.
"""

from __future__ import annotations

from src.agent.nodes.checker import FaithfulnessVerdict, check_faithfulness
from src.agent.nodes.citation_validator import (
    citation_validator_node,
    extract_prose_sections,
    validate_citations,
)
from src.agent.nodes.fast_path import (
    build_fast_path_answer,
    detect_exact_section,
    lookup_section_chunks,
)
from src.agent.nodes.generator import (
    _format_context,
    generate_answer,
)
from src.agent.nodes.grader import GradeVerdict, grade_chunks
from src.agent.nodes.intent_expander import (
    SubQueries,
)
from src.agent.nodes.ood_gate import is_out_of_domain
from src.agent.nodes.rewriter import RewrittenQuery
from src.agent.nodes.router import RouteDecision, router_node
from src.ingest.chunk_chonkie import LegalChunk
from src.models.schemas import Citation, LegalAdvice
from src.retrieval.hybrid import RetrievedChunk


class _FakeClient:
    """Stand-in for the instructor client: `.create(...)` returns a canned model.

    Records the messages it was called with so tests can assert the query made
    it into the prompt. Zero quota, no key needed.
    """

    def __init__(self, route: str) -> None:
        self._route = route
        self.calls: list[dict] = []

    def create(self, *, messages, response_model, **kwargs):  # noqa: ANN001
        self.calls.append({"messages": messages, "response_model": response_model, **kwargs})
        assert response_model is RouteDecision
        return RouteDecision(route=self._route)


class _FakeExpanderClient:
    """Returns canned sub-queries for the intent expander. Zero quota."""

    def __init__(self, subs: list[str]) -> None:
        self._subs = subs
        self.calls: list[dict] = []

    def create(self, *, messages, response_model, **kwargs):  # noqa: ANN001
        self.calls.append({"messages": messages, "response_model": response_model, **kwargs})
        assert response_model is SubQueries
        return SubQueries(sub_queries=self._subs)


class _FakeAsyncGraderClient:
    """Async stand-in for the grader's client: `.create` is awaited.

    Verdicts are keyed by section_id so a test can make specific chunks pass/fail;
    unknown sections default to `default`. Records call count. Zero quota.
    """

    def __init__(self, by_section: dict[str, bool], *, default: bool = False) -> None:
        self._by_section = by_section
        self._default = default
        self.n_calls = 0
        self.closed = False

    async def create(self, *, messages, response_model, **kwargs):  # noqa: ANN001
        self.n_calls += 1
        assert response_model is GradeVerdict
        # pull the section id out of the rendered prompt ("... Section <id>: ...")
        content = messages[0]["content"]
        relevant = self._default
        for sid, verdict in self._by_section.items():
            if f"Section {sid}:" in content:
                relevant = verdict
                break
        return GradeVerdict(relevant=relevant)

    async def aclose(self) -> None:
        self.closed = True


class _FakeRewriterClient:
    """Returns a canned rewritten query. Records the rendered prompt. Zero quota."""

    def __init__(self, rewritten: str) -> None:
        self._rewritten = rewritten
        self.calls: list[dict] = []

    def create(self, *, messages, response_model, **kwargs):  # noqa: ANN001
        self.calls.append({"messages": messages, "response_model": response_model, **kwargs})
        assert response_model is RewrittenQuery
        return RewrittenQuery(query=self._rewritten)


class _FakeGeneratorClient:
    """Returns a canned LegalAdvice. Records the rendered prompt. Zero quota."""

    def __init__(self, advice: LegalAdvice) -> None:
        self._advice = advice
        self.calls: list[dict] = []

    def create(self, *, messages, response_model, **kwargs):  # noqa: ANN001
        self.calls.append({"messages": messages, "response_model": response_model, **kwargs})
        assert response_model is LegalAdvice
        return self._advice.model_copy(deep=True)


class _FakeCheckerClient:
    """Returns a canned faithfulness verdict. Records the rendered prompt. Zero quota."""

    def __init__(self, faithful: bool) -> None:
        self._faithful = faithful
        self.calls: list[dict] = []

    def create(self, *, messages, response_model, **kwargs):  # noqa: ANN001
        self.calls.append({"messages": messages, "response_model": response_model, **kwargs})
        assert response_model is FaithfulnessVerdict
        return FaithfulnessVerdict(faithful=self._faithful)


# A tiny IPC->BNS map so the IPC-normalization tests don't need the real PDF.
IPC_MAP = {"302": "103", "379": "303", "420": "318"}


def _rc(dense_score: float | None) -> RetrievedChunk:
    chunk = LegalChunk("BNS::103::0", "BNS", "103", "Punishment for murder", "text")
    return RetrievedChunk(chunk=chunk, rrf_score=0.5, dense_score=dense_score)


class TestExactSectionDetection:
    def test_detects_explicit_bns_section(self) -> None:
        assert detect_exact_section("what is BNS Section 103") == ("BNS", "103")

    def test_normalizes_ipc_reference(self) -> None:
        """'302 IPC' should resolve to its BNS equivalent (103) via the mapping."""
        assert detect_exact_section("explain section 302 IPC", ipc_bns_mapping=IPC_MAP) == (
            "BNS",
            "103",
        )


class TestLookupSection:
    def test_fast_path_reassembles_all_section_chunks(self) -> None:
        chunks = [
            LegalChunk("BNS::303::1", "BNS", "303", "Theft", "Heading\n\nsecond", "Heading"),
            LegalChunk("BNS::303::0", "BNS", "303", "Theft", "Heading\n\nfirst", "Heading"),
        ]
        section_chunks = lookup_section_chunks("BNS", "303", chunks)
        answer = build_fast_path_answer("BNS 303", section_chunks)

        assert answer.answer.endswith("first second")
        assert answer.citations[0].section_id == "303"

    def test_fast_path_surfaces_enriched_classification(self) -> None:
        # cognizable/bailable/category are already on the chunk (enrich_metadata);
        # the deterministic answer should report them, no LLM.
        chunk = LegalChunk(
            "BNS::103::0",
            "BNS",
            "103",
            "Punishment for murder",
            "body",
            metadata={
                "cognizable": True,
                "bailable": False,
                "offence_category": "Of Offences Affecting The Human Body",
            },
        )
        answer = build_fast_path_answer("BNS 103", [chunk])
        assert "cognizable" in answer.answer
        assert "non-bailable" in answer.answer
        assert "Of Offences Affecting The Human Body" in answer.answer


class TestOutOfDomainGate:
    def test_far_chunk_is_ood(self) -> None:
        # similarity 0.1 -> distance 0.9 > 0.75
        assert is_out_of_domain([_rc(0.1)]) is True

    def test_threshold_boundary_is_in_domain(self) -> None:
        # similarity 0.25 -> distance exactly 0.75, strict > means in-domain
        assert is_out_of_domain([_rc(0.25)]) is False


class TestRouterUnit:
    """Node logic against a fake client — no key, no quota."""

    def test_out_of_scope_gets_canned_low_confidence_answer(self) -> None:
        out = router_node({"query": "how do I file taxes"}, client=_FakeClient("out_of_scope"))
        assert out["route"] == "out_of_scope"
        assert out["answer"].confidence == "low"
        assert out["answer"].in_corpus is False


def _chunk(section_id: str) -> RetrievedChunk:
    """A RetrievedChunk for a given BNS section (for grader fan-out tests)."""
    c = LegalChunk(f"BNS::{section_id}::0", "BNS", section_id, f"Heading {section_id}", "body text")
    return RetrievedChunk(chunk=c, rrf_score=0.5)


class TestGraderUnit:
    """Parallel grade + filter against a fake async client — no key, no quota."""

    def test_grade_chunks_keeps_only_relevant(self) -> None:
        chunks = [_chunk("103"), _chunk("303"), _chunk("318")]
        fake = _FakeAsyncGraderClient({"103": True, "303": False, "318": True})
        kept = grade_chunks("murder or cheating", chunks, client=fake)
        assert [c.chunk.section_id for c in kept] == ["103", "318"]
        assert fake.n_calls == 3  # one call per chunk (the fan-out)


class TestGeneratorUnit:
    """Cited-advice assembly against a fake client — no key, no quota."""

    def _canned(self) -> LegalAdvice:
        return LegalAdvice(
            query="(model may set this)",
            answer="Murder is punished under BNS 103.",
            citations=[Citation(act="BNS", section_id="103", heading="Punishment for murder")],
            offences_identified=["murder"],
            in_corpus=False,  # generator must overwrite this to True
        )

    def test_punishment_instruction_preserves_bounds_and_fine(self) -> None:
        fake = _FakeGeneratorClient(self._canned())
        wallet = _chunk("314")
        wallet.chunk.text = (
            "shall not be less than six months but may extend to two years and with fine"
        )
        generate_answer("I kept a lost wallet", [wallet], client=fake)
        content = fake.calls[0]["messages"][0]["content"]
        assert "not be less than six months" in content
        assert "fine is mandatory or optional" in content
        assert "exactly from the cited text" in content

    def test_citation_repair_omits_rejected_subsection_body(self) -> None:
        chunk = LegalChunk(
            "BNS::106::0",
            "BNS",
            "106",
            "Causing death by negligence",
            "(1) Five years for causing death by negligence.\n"
            "(2) Ten years after fleeing without reporting.",
        )
        context = _format_context(
            [RetrievedChunk(chunk=chunk, rrf_score=0.5)],
            invalid_citations=["BNS 106(2) (not in force)"],
        )

        assert "Five years" in context
        assert "Ten years" not in context
        assert "Rejected subsection omitted" in context


def _advice(citations: list[tuple[str, str]], answer: str = "some legal answer") -> LegalAdvice:
    """A LegalAdvice citing the given (act, section_id) pairs."""
    return LegalAdvice(
        query="q",
        answer=answer,
        citations=[Citation(act=a, section_id=s) for a, s in citations],
    )


class TestCitationValidator:
    """The headline piece: pure-code check that every cited section was retrieved."""

    def test_prose_only_sections_are_rejected(self) -> None:
        adv = _advice(
            [("BNS", "336"), ("BNS", "89")],
            answer="BNS Sections 336 and 338 apply. Sections 89 and 85 may also apply.",
        )
        assert extract_prose_sections(adv) == [
            ("BNS", "336"),
            ("BNS", "338"),
            (None, "89"),
            (None, "85"),
        ]
        valid, invalid = validate_citations(
            adv,
            [_chunk("336"), _chunk("338"), _chunk("89"), _chunk("85")],
        )
        assert valid is False
        assert invalid == ["BNS 338", "SECTION 85"]

    def test_fabricated_citation_is_rejected(self) -> None:
        # THE demo: answer cites BNS 307 but only 306 was retrieved -> caught.
        adv = _advice([("BNS", "306"), ("BNS", "307")])
        retrieved = [_chunk("306")]
        valid, invalid = validate_citations(adv, retrieved)
        assert valid is False
        assert invalid == ["BNS 307"]

    def test_uncommenced_subsection_is_rejected(self) -> None:
        adv = _advice(
            [("BNS", "106")],
            answer="BNS Section 106(1) applies, but Section 106(2) increases the punishment.",
        )
        valid, invalid = validate_citations(adv, [_chunk("106")])
        assert valid is False
        assert invalid == ["BNS 106(2) (not in force)"]

    def test_node_rejects_section_excluded_from_generation_context(self) -> None:
        adv = _advice([("BNS", "999")])
        out = citation_validator_node(
            {
                "answer": adv,
                "relevant_chunks": [_chunk("103")],
                "retrieved": [_chunk("103"), _chunk("999")],
            }
        )
        assert out["citation_valid"] is False
        assert out["invalid_citations"] == ["BNS 999"]


class TestCheckerUnit:
    """Faithfulness pass against a fake client — no key, no quota."""

    def test_unfaithful_verdict(self) -> None:
        adv = _advice([("BNS", "103")], answer="Murder carries a mandatory death sentence.")
        fake = _FakeCheckerClient(faithful=False)
        faithful, unsupported = check_faithfulness(adv, [_chunk("103")], client=fake)
        assert faithful is False
        assert unsupported == []
