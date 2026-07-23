"""Offline claim-level faithfulness audit for saved answer traces."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.eval.ragas_eval import read_samples

FailureType = Literal[
    "extra_detail",
    "wrong_application",
    "missing_condition",
    "wrong_punishment",
    "unsupported_procedure",
    "retrieval_miss",
    "other",
]

_EXTRACT_PROMPT = """Split this Indian criminal-law answer into atomic, independently
checkable legal or factual claims. Include offence classifications, elements,
conditions, punishments, procedures, and practical remedies. Ignore the generic
legal-advice disclaimer.

Each claim must be a neutral restatement of something the answer actually says.
Keep an exact contiguous quote from the answer for traceability. Do not add implied
exceptions, missing qualifications, outside facts, or criticism. Preserve logical
operators and qualifiers. In particular, do not split "A or B" into separate claims
that say the result is only A or only B. Either keep the alternatives together or say
that each is one possible alternative. Keep mandatory additions such as "and also a
fine" attached when separating them would change the legal meaning.

Question:
{question}

Answer:
{answer}
"""

_VERIFY_PROMPT = """Audit these fixed claims only against the retrieved contexts below.

For each claim:
- supported is true only when the contexts entail the whole claim.
- context_ids lists every supporting context, using IDs such as C1.
- evidence_quote is a short exact quote. Leave it null when unsupported.
- failure_type is null when supported. Otherwise choose the closest supplied category.
- reason briefly explains the verdict without using outside legal knowledge.

Return exactly one verdict for every supplied claim ID. Do not create, merge, split,
or rewrite claims. Do not penalize a claim merely because the answer omitted another
rule or exception. Treat facts stated in the question as given. A general statutory
rule supports its application to those facts even when the statute does not repeat a
fact-specific word such as "stabbing." Judge whether the claim is entailed, not
whether its exact sentence appears verbatim. Judge each claim independently. Do not
reject a correct punishment or rule merely because another claim applied its offence
to the facts incorrectly. Treat "imprisonment plus fine" as imprisonment and fine,
not as two alternatives. Before returning, make sure the supported boolean agrees
with the written reason.

Use retrieval_miss only when no retrieved context contains an applicable rule or
evidence for the claim. Use wrong_application when the rule is present but the answer
maps the facts to the wrong offence. Use extra_detail for an unsupported side point,
missing_condition for a rule stated without a required condition, wrong_punishment
for an incorrect penalty, unsupported_procedure for an ungrounded procedural claim,
and other when none of those fits.

Question:
{question}

Claims:
{claims}

Retrieved contexts:
{contexts}

The act and section labels attached to each context are authoritative. Do not infer
a different statute from wording or numbering.
"""


class ExtractedClaim(BaseModel):
    claim: str = Field(min_length=1)
    answer_quote: str = Field(min_length=1)


class ClaimExtraction(BaseModel):
    claims: list[ExtractedClaim] = Field(min_length=1)


class ClaimVerdict(BaseModel):
    claim_id: str = Field(pattern=r"^K[1-9]\d*$")
    supported: bool
    context_ids: list[str] = Field(default_factory=list)
    evidence_quote: str | None = None
    failure_type: FailureType | None = None
    reason: str = Field(min_length=1)


class ClaimVerdicts(BaseModel):
    verdicts: list[ClaimVerdict] = Field(min_length=1)


@dataclass
class ClaimAuditSummary:
    scenarios: int
    claims: int
    valid_claims: int
    invalid_claims: int
    supported_claims: int
    support_ratio: float
    failure_types: dict[str, int]


def _judge_client():
    """Build one Instructor client from the same pinned profile as RAGAS."""
    import instructor
    from openai import OpenAI

    from src.agent.llm import _judge_profile

    profile = _judge_profile()
    return (
        instructor.from_openai(
            OpenAI(
                base_url=profile.base_url,
                api_key=profile.api_key,
                timeout=profile.timeout,
                max_retries=0,
            ),
            mode=instructor.Mode.TOOLS,
        ),
        profile,
    )


def _source_by_text(corpus) -> dict[str, str]:
    return {
        chunk.text: f"{chunk.act} Section {chunk.section_id}: {chunk.heading}" for chunk in corpus
    }


def _render_contexts(contexts: list[str], source_by_text: dict[str, str]) -> str:
    rendered = []
    for i, text in enumerate(contexts, start=1):
        source = source_by_text.get(text)
        label = f"C{i} | {source}" if source else f"C{i} | source unavailable"
        rendered.append(f"[{label}] {text}")
    return "\n\n".join(rendered)


def _quote_is_from_answer(quote: str, answer: str) -> bool:
    def _normalize(text: str) -> str:
        for marker in ("**", "__", "`"):
            text = text.replace(marker, "")
        text = text.translate(str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"}))
        text = text.replace('"', "").replace("'", "")
        return " ".join(text.split()).casefold()

    normalized_quote = _normalize(quote)
    normalized_answer = _normalize(answer)
    return normalized_quote in normalized_answer or (
        bool(anchor := normalized_quote.rstrip(".,;:!?")) and anchor in normalized_answer
    )


def _completion_record(stage: str, completion, requested_model: str) -> dict:
    usage = getattr(completion, "usage", None)
    return {
        "stage": stage,
        "requested_model": requested_model,
        "reported_model": getattr(completion, "model", requested_model),
        "input_tokens": getattr(usage, "prompt_tokens", None),
        "output_tokens": getattr(usage, "completion_tokens", None),
    }


def _judge_consistent(claim: dict) -> bool:
    if claim["supported"]:
        return True
    reason = claim["reason"].casefold()
    return not any(
        phrase in reason for phrase in ("claim is actually correct", "this is actually supported")
    )


def _create(client, profile, *, prompt: str, response_model):
    extra_body = {"thinking": {"type": "disabled"}} if profile.disable_thinking else None
    return client.create_with_completion(
        model=profile.model,
        messages=[{"role": "user", "content": prompt}],
        response_model=response_model,
        temperature=0,
        max_tokens=profile.max_tokens,
        max_retries=0,
        **({"extra_body": extra_body} if extra_body else {}),
    )


def audit_row(row: dict, *, client, profile, source_by_text: dict[str, str]) -> dict:
    """Audit one saved answer and retain provider provenance."""
    question = row.get("user_input")
    answer = row.get("response")
    contexts = row.get("retrieved_contexts")
    if not isinstance(question, str) or not isinstance(answer, str):
        raise ValueError("sample needs string user_input and response fields")
    if not isinstance(contexts, list) or not all(isinstance(text, str) for text in contexts):
        raise ValueError("sample needs a string list in retrieved_contexts")

    extraction, extraction_completion = _create(
        client,
        profile,
        prompt=_EXTRACT_PROMPT.format(question=question, answer=answer),
        response_model=ClaimExtraction,
    )
    for claim in extraction.claims:
        if not _quote_is_from_answer(claim.answer_quote, answer):
            raise ValueError(f"claim quote is not in the answer: {claim.answer_quote!r}")

    claims_by_id = {
        f"K{i}": {"claim": claim.claim, "answer_quote": claim.answer_quote}
        for i, claim in enumerate(extraction.claims, start=1)
    }
    verdicts, verdict_completion = _create(
        client,
        profile,
        prompt=_VERIFY_PROMPT.format(
            question=question,
            claims="\n".join(
                f"[{claim_id}] {claim['claim']}" for claim_id, claim in claims_by_id.items()
            ),
            contexts=_render_contexts(contexts, source_by_text),
        ),
        response_model=ClaimVerdicts,
    )
    verdicts_by_id = {verdict.claim_id: verdict for verdict in verdicts.verdicts}
    if len(verdicts_by_id) != len(verdicts.verdicts):
        raise ValueError("claim audit returned duplicate claim IDs")
    if verdicts_by_id.keys() != claims_by_id.keys():
        raise ValueError("claim audit did not return every extracted claim ID")

    claims = []
    for claim_id, claim in claims_by_id.items():
        verdict = verdicts_by_id[claim_id]
        finding = {
            "claim_id": claim_id,
            **claim,
            "supported": verdict.supported,
            "context_ids": verdict.context_ids,
            "evidence_quote": verdict.evidence_quote if verdict.supported else None,
            "failure_type": None if verdict.supported else (verdict.failure_type or "other"),
            "reason": verdict.reason,
        }
        finding["judge_consistent"] = _judge_consistent(finding)
        claims.append(finding)
    valid = [claim for claim in claims if claim["judge_consistent"]]
    supported = sum(claim["supported"] for claim in valid)
    calls = [
        _completion_record("claim_extraction", extraction_completion, profile.model),
        _completion_record("claim_verification", verdict_completion, profile.model),
    ]
    return {
        "scenario_id": row.get("scenario_id", "?"),
        "judge_calls": calls,
        "input_tokens": sum(call["input_tokens"] or 0 for call in calls),
        "output_tokens": sum(call["output_tokens"] or 0 for call in calls),
        "claim_count": len(claims),
        "valid_claims": len(valid),
        "invalid_claims": len(claims) - len(valid),
        "supported_claims": supported,
        "support_ratio": supported / len(valid) if valid else 0.0,
        "claims": claims,
    }


def summarize(rows: list[dict]) -> ClaimAuditSummary:
    claims = sum(row["claim_count"] for row in rows)
    findings = [claim for row in rows for claim in row["claims"]]
    valid = [claim for claim in findings if _judge_consistent(claim)]
    supported = sum(claim["supported"] for claim in valid)
    failures = Counter(
        claim["failure_type"] for claim in valid if not claim["supported"] and claim["failure_type"]
    )
    return ClaimAuditSummary(
        scenarios=len(rows),
        claims=claims,
        valid_claims=len(valid),
        invalid_claims=claims - len(valid),
        supported_claims=supported,
        support_ratio=supported / len(valid) if valid else 0.0,
        failure_types=dict(sorted(failures.items())),
    )


def write_audits(rows: list[dict], path: str | Path) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_audits(path: str | Path) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()]


def run_claim_audit(
    samples_in: str | Path,
    audits_out: str | Path,
    *,
    limit: int | None = None,
    scenario_ids: set[str] | None = None,
    resume: bool = False,
    client=None,
    profile=None,
    corpus=None,
) -> ClaimAuditSummary:
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    rows = read_samples(samples_in)
    if scenario_ids:
        rows = [row for row in rows if row.get("scenario_id") in scenario_ids]
        found = {row.get("scenario_id") for row in rows}
        if missing := scenario_ids - found:
            raise ValueError(f"scenario IDs not found: {', '.join(sorted(missing))}")
    if limit is not None:
        rows = rows[:limit]
    if client is None or profile is None:
        client, profile = _judge_client()
    if corpus is None:
        from src.retrieval.index import load_chunks

        corpus = load_chunks("data/processed/sections.jsonl")
    sources = _source_by_text(corpus)
    output = Path(audits_out)
    audits = read_audits(output) if resume and output.exists() else []
    completed = {row.get("scenario_id") for row in audits}
    if len(completed) != len(audits):
        raise ValueError("existing audit has duplicate scenario IDs")
    if any(
        call.get("requested_model") != profile.model
        for row in audits
        for call in row.get("judge_calls", [])
    ):
        raise ValueError("existing audit used a different requested judge model")
    rows = [row for row in rows if row.get("scenario_id") not in completed]
    write_audits(audits, audits_out)
    for row in rows:
        audits.append(audit_row(row, client=client, profile=profile, source_by_text=sources))
        write_audits(audits, audits_out)
    return summarize(audits)


def main() -> None:  # pragma: no cover
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Audit saved RAG answers at claim level")
    parser.add_argument("--samples-in", type=Path, required=True)
    parser.add_argument("--audits-out", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--scenario-id", action="append")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    summary = run_claim_audit(
        args.samples_in,
        args.audits_out,
        limit=args.limit,
        scenario_ids=set(args.scenario_id or []),
        resume=args.resume,
    )
    print(json.dumps(asdict(summary), indent=2))


if __name__ == "__main__":
    main()
