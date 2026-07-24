# RAGAS results

This records the full runs over the 50 hand-labelled scenarios in
`data/eval/scenarios.jsonl` (19 easy, 24 medium, 7 hard). The runs are
diagnostics, not production-accuracy claims. Model provenance is part of each
result because the latest routing experiment does not use the earlier
DeepSeek-only answer path.

## Earlier DeepSeek-only setup

- Agent: DeepSeek V4 Flash for routing, expansion, grading, rewriting, and
  checking. DeepSeek V4 Pro wrote the final answer. Thinking was disabled.
- RAGAS judge: DeepSeek V4 Flash at temperature 0 with a 256-token ceiling.
- Answer-relevancy embeddings: local `BAAI/bge-small-en-v1.5`.
- Corpus: the 1,151-chunk local BNS, BNSS, and BSA index after sentence-aware
  chunk repair.
- Scoring: RAGAS `strictness=1` and eight judge workers. The output traces and
  score manifests are local evaluation artifacts and are not committed.

The current-routing run has its own provenance below. It used a 4,096-token
judge ceiling, two workers, and bounded retries so long metric responses and
transient provider failures did not invalidate the saved answer collection.

## Overall scores

The first two rows are the older full-graph runs (router + expander + grader +
checker + rewrite loop). The remaining rows use the simpler production pipeline:
dense retrieval, no reranker, generation, deterministic citation validation,
and the scope/OOD controls. The final three include one bounded citation repair.
The final two tighten the generator around the central fact-supported rule, and
the last row adds guards for cross-referenced punishments and closed statutory
tables. The first four rows use the recorded 1,151-chunk corpus. The last four
use the rebuilt 1,155-chunk corpus. All eight use the same 50 scenarios.

| pipeline / retrieval | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| full graph, dense, no reranker | 0.309 | 0.518 | 0.700 | 0.840 |
| full graph, hybrid RRF + reranker | 0.314 | 0.386 | **0.709** | 0.732 |
| production, dense, no reranker, DeepSeek only | 0.517 | **0.749** | 0.615 | 0.919 |
| production, dense, no reranker, current routing | 0.496 | 0.689 | 0.630 | 0.912 |
| production, dense, no reranker, post-fix routing | 0.470 | 0.612 | 0.629 | **0.988** |
| production, dense, no reranker, bounded repair | 0.517 | 0.686 | 0.607 | 0.975 |
| production, dense, no reranker, grounded answers | **0.591** | 0.665 | 0.607 | 0.952 |
| production, dense, no reranker, claim guards | 0.543 | 0.687 | 0.622 | **0.988** |

The production path is the decisive result. Dropping the checker and rewrite loop
nearly doubles faithfulness (0.309 → 0.517) and answer relevancy (0.518 → 0.749),
and lifts context recall to 0.919. Context precision dips (0.700 → 0.615), which
is consistent with the wider 12-chunk answer window feeding more context in. The
20-case node ablation and the ten-answer statute audit both predicted that the
simple path would beat the full graph on answer quality; this full 50-scenario
run on the actual production pipeline confirms it. Faithfulness at 0.517 is still
middling, so this stays a local demo, but the "coverage is better than the final
answers" gap the earlier full-graph runs showed is largely closed.

Provenance: judge and control nodes on `deepseek-v4-flash`, answers on
`deepseek-v4-pro`, thinking disabled. Every one of the 50 production scenarios
returned a generated answer; none fell back to the canned low-confidence reply,
unlike the full-graph runs where the checker-to-rewriter loop ended 13–20
scenarios in low confidence.

### Current routing run

The 2026-07-18 run tested the two-tier routing setup rather than repeating the
DeepSeek-only model assignment. `mistral/mistral-small-latest` completed all 50
control calls. Answer generation recorded 46 successful
`nvidia/nvidia/nemotron-3-ultra-550b-a55b` calls and 6 successful paid
`deepseek/deepseek-v4-pro` fallback calls. NVIDIA also returned 4 failed
attempts. A few graph paths generated more than once, so the 52 successful
generation calls should not be read as 52 scenarios.

The answer trace was saved before judging. It contains all 50 scenarios, one
low-confidence answer, no empty answers, and citations in every row. The final
judge pass reused that trace and completed 200 paid
`deepseek/deepseek-v4-flash` metric jobs with no missing result. This matters for
cost control because judge retries did not trigger another answer collection.

The current-routing result is close to the older DeepSeek-only production run
on context precision and recall, but lower on faithfulness and answer
relevancy. It is not a clean model-quality comparison because both the control
and answer models changed. It does show that the cheaper mixed route can finish
the full workload while keeping paid Pro calls to fallback cases.

| difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| easy (19) | 0.445 | 0.670 | 0.622 | 0.982 |
| medium (24) | 0.542 | 0.701 | 0.619 | 0.927 |
| hard (7) | 0.474 | 0.697 | 0.692 | 0.670 |

The NVIDIA Mistral Small 4 judge still works for a one-sample connectivity
check, but it did not complete the full suite reliably. Long outputs truncated
at smaller token ceilings. After that was raised, one upstream 502 put the only
NVIDIA judge connection into cooldown and the remaining jobs failed. I deleted
that partial score rather than reporting a mixed valid/invalid aggregate. The
pinned NVIDIA alias remains useful for small development checks; the full valid
run used the paid release judge.

### Post-fix trace and manual audit

I collected the fixed system over the same 50 scenarios on 2026-07-22 and saved
the answers before judging. The production path used dense retrieval without a
reranker on the rebuilt 1,155-chunk index. Mistral Small completed 50 control
calls. Answer generation completed 39 NVIDIA Nemotron 3 Ultra calls and 11 paid
DeepSeek V4 Pro fallbacks after 11 NVIDIA 503 responses.

The trace has 50 rows and no empty answers. Six scenarios ended at low confidence
after deterministic citation validation: s07, s12, s13, s33, s34, and s40. The
s13 rejection is the intended guard against presenting uncommenced BNS 106(2) as
current law.

The manual audit found 31 passes, 12 partial answers, and 7 failures. The clean
pass rate rose from 56% to 62%, while the pass-or-partial rate fell from 88% to
86%. Five earlier material failures are clean passes now, but five earlier
partial answers became generic validator refusals. The local artifact is
`data/eval/ragas-post-fix-routing-50.jsonl`, and the row record is in
[post-fix-answer-audit.md](post-fix-answer-audit.md).

The judge-only pass reused that trace and completed all 200 metric calls on paid
`deepseek/deepseek-v4-flash`. Thinking was disabled, matching the successful
release-judge behavior from the earlier run. It used 369,141 input tokens and
31,970 output tokens, with no failed metric job. The final scores are 0.470
faithfulness, 0.612 answer relevancy, 0.629 context precision, and 0.988 context
recall. Compared with the earlier current-routing trace, context recall gained
0.076 while faithfulness fell 0.025 and answer relevancy fell 0.077. Context
precision was effectively unchanged.

| difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| easy (19) | 0.474 | 0.640 | 0.643 | 0.982 |
| medium (24) | 0.422 | 0.558 | 0.589 | 0.990 |
| hard (7) | 0.626 | 0.718 | 0.732 | 1.000 |

The retrieval fixes reached the difficult slice, but the final answer path did
not convert all of that context into usable answers. The manual audit and RAGAS
now point to the same next change: repair a citation-invalid draft once before
returning the generic refusal.

### Six-case citation-repair diagnostic

I froze the six post-fix scenarios that had returned generic validator refusals:
`s07`, `s12`, `s13`, `s33`, `s34`, and `s40`. I then saved a new answer trace on
the same 1,155-chunk index with dense retrieval and no reranker. The production
graph returned six high-confidence, citation-valid answers. Two drafts needed the
new repair path: `s13` removed uncommenced BNS 106(2), while `s33` removed a
fabricated Section 141 reference. The other four passed on their first draft in
this run.

| saved six-case trace | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| old generic refusals | 0.000 | 0.000 | 0.456 | 1.000 |
| current pipeline with bounded repair | **0.595** | **0.672** | 0.450 | 1.000 |

Both saved traces were judged separately with pinned paid
`deepseek/deepseek-v4-flash`, thinking disabled, two workers, and no answer
regeneration. Each pass completed 98 successful provider requests with no
fallback: 192,339 input and 11,299 output tokens for the baseline, then 189,359
input and 16,717 output tokens for the repaired trace. The answer trace used
Mistral Small for routing and the two bounded repairs, and NVIDIA Nemotron 3
Ultra for initial answers. Provider logs recorded 10 successful Mistral requests
and 7 successful NVIDIA requests, including structured-output retries, with no
paid answer fallback.

This is a targeted regression check, not a new headline score. Only two of the
six final answers exercised the repair node, and model variation let the other
four pass on their first attempt. The result shows that the failure-aware repair
can recover the two observed invalid drafts without weakening citation
validation. The full result below now replaces this diagnostic as the current
headline run.

### Final bounded-repair run

I collected the final 50 answers before judging. The run used the production
graph, dense retrieval, no reranker, and the 1,155-chunk index. Mistral Small
made 50 router calls and six repair calls. NVIDIA Nemotron 3 Ultra completed 45
initial answers and returned five 503 errors. Paid DeepSeek V4 Pro handled those
five fallbacks. The saved trace has 49 high-confidence answers, one
low-confidence refusal, and no empty rows.

Six drafts entered repair. Five passed the deterministic validator after repair,
although the manual audit still failed one of those answers. The audit found 35
passes, 13 partial answers, and 2 failures. That is a 70% clean-pass rate and a
96% pass-or-partial rate. The row record is in
[final-repair-answer-audit.md](final-repair-answer-audit.md).

The judge-only pass reused `data/eval/ragas-final-repair-50.jsonl`. Pinned paid
`deepseek/deepseek-v4-flash` ran with thinking disabled, two workers, two bounded
retries, and a 4,096-token ceiling. All 200 metric jobs completed. RAGAS and its
structured-output retries produced 856 successful provider requests, using
1,725,442 input tokens and 142,484 output tokens. There was no judge fallback
and no answer regeneration.

| difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| easy (19) | 0.535 | 0.655 | 0.621 | 0.982 |
| medium (24) | 0.464 | 0.696 | 0.567 | 0.962 |
| hard (7) | 0.654 | 0.734 | 0.705 | 1.000 |
| **overall (50)** | **0.517** | **0.686** | **0.607** | **0.975** |

Against the post-fix run, faithfulness improved by 0.047 and answer relevancy by
0.074. Context precision fell by 0.022 and context recall by 0.013. The repair
mainly fixed answer usability: generic refusals fell from six to one, and the
manual failure count fell from seven to two. Faithfulness is still only 0.517,
so this remains a supervised local demo rather than a legal-answer service.

### Grounded-answer run

The generator prompt now keeps the answer under 180 words, uses the smallest
sufficient set of sections, and excludes a related offence unless the question
supplies its statutory conditions. It also forbids borrowing a punishment from
a nearby section. This is still the same production graph. I did not add another
checker or repair loop.

I first tested six frozen problem cases: `s04`, `s07`, `s11`, `s16`, `s30`, and
`s46`. The saved bounded-repair answers scored 0.309 faithfulness, while the new
answers scored 0.573 with the same judge. Answer relevancy moved from 0.669 to
0.652, context precision from 0.507 to 0.577, and context recall stayed 0.958.
The old judge pass recorded 98 successful DeepSeek V4 Flash calls plus four
transient 524 responses, using 194,707 input and 17,470 output tokens. The new
pass recorded 98 successful calls with no failed request, using 193,937 input
and 15,865 output tokens.

The milestone trace then ran all `s01-s50` scenarios on the 1,155-chunk index,
dense retrieval, no reranker, and the production graph. It contains 50
high-confidence answers, no empty or unfinished answer, and three bounded
citation repairs. Average answer length fell from 119 to 101 words. Provider
logs recorded 55 successful Mistral Small calls with 150,006 input and 1,190
output tokens. NVIDIA Nemotron 3 Ultra recorded 41 successes and nine 503s,
using 234,123 input and 10,380 output tokens on successful calls. Paid DeepSeek
V4 Pro recorded 11 successful fallback or structured-output calls, using 60,129
input and 4,588 output tokens. Extra successful calls are retries, not extra
scenarios.

The judge-only pass reused `data/eval/ragas-grounded-final-50.jsonl`. Pinned paid
`deepseek/deepseek-v4-flash` ran with thinking disabled, two workers, two bounded
retries, and a 4,096-token ceiling. All 200 metric jobs completed. RAGAS and its
structured-output retries produced 856 successful provider calls, using
1,721,952 input and 136,562 output tokens. No answer was regenerated.

| difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| easy (19) | 0.606 | 0.680 | 0.602 | 0.982 |
| medium (24) | 0.595 | 0.647 | 0.573 | 0.913 |
| hard (7) | 0.538 | 0.685 | 0.731 | 1.000 |
| **overall (50)** | **0.591** | **0.665** | **0.607** | **0.952** |

Against the bounded-repair run, faithfulness improved by 0.074. Answer
relevancy fell by 0.021, context precision was unchanged after rounding, and
context recall fell by 0.023. This is the current headline RAGAS result. I have
not given this trace the same row-by-row legal audit as the bounded-repair trace,
so the 70% clean-pass and 96% usable rates still belong only to that earlier
trace.

### Production run difficulty slices

| difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| easy | 0.423 | 0.749 | 0.632 | 0.982 |
| medium | 0.550 | 0.748 | 0.570 | 0.941 |
| hard | 0.661 | 0.754 | 0.726 | 0.670 |

Answer relevancy is flat across difficulty. Faithfulness is actually highest on
the seven hard scenarios and lowest on the easy ones — the easy tier is where the
generator most often overreaches slightly beyond the retrieved text. The hard
tier's context recall (0.670) is the weakest retrieval spot, as before.

## Difficulty slices

| retrieval | difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---|---:|---:|---:|---:|
| dense, no reranker | easy | 0.320 | 0.515 | 0.784 | 0.947 |
| dense, no reranker | medium | 0.330 | 0.540 | 0.663 | 0.817 |
| dense, no reranker | hard | 0.207 | 0.451 | 0.595 | 0.625 |
| hybrid RRF + reranker | easy | 0.271 | 0.366 | 0.680 | 0.772 |
| hybrid RRF + reranker | medium | 0.307 | 0.356 | 0.718 | 0.722 |
| hybrid RRF + reranker | hard | 0.458 | 0.543 | 0.762 | 0.660 |

The seven-item hard slice is too small to settle the retrieval choice by itself.
It is useful as a warning that the score changes by difficulty.

## What the traces show

The deterministic citation validator accepted every generated answer in both
runs: 93 dense attempts and 99 hybrid attempts. The LLM checker rejected 56
dense attempts and 62 hybrid attempts. That caused 44 dense query rewrites and
49 hybrid rewrites. Thirteen dense queries and twenty hybrid queries then ended
with a low-confidence response.

This points at answer grounding and the checker-to-rewriter recovery path, not
at missing retrieval context alone. A checker failure currently changes the
query, often returns similar context, and can fail again. The checked answer is
then replaced with a low-confidence response even when the grader found several
relevant sections.

## 20-scenario node ablation

The full 50-case loops were too expensive to repeat for every node combination.
I instead ran all four variants on the same 20-case stratified random sample:
eight easy, nine medium, and three hard scenarios. The sample uses
`random.Random(20260713)` and contains `s06, s18, s07, s29, s19, s48, s38, s45,
s12, s37, s27, s25, s13, s50, s43, s35, s05, s17, s03, s28`.

Each run used DeepSeek V4 Flash for control and judging, V4 Pro for answers,
dense retrieval without reranking, and the same local corpus. The traces and
score manifests record the model, sample IDs, citations, and answer status.

| pipeline | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| baseline | **0.433** | **0.718** | 0.737 | 0.796 |
| baseline + grader | 0.426 | 0.714 | **0.844** | 0.823 |
| baseline + grader + checker | 0.186 | 0.310 | 0.789 | 0.794 |
| current full graph | 0.341 | 0.501 | 0.778 | **0.892** |

The variants are:

1. `baseline`: retrieve, generate, then validate citations.
2. `grader`: baseline plus the relevance grader.
3. `checker`: grader plus the faithfulness checker, without query retries.
4. `full`: the existing router, expander, OOD gate, checker, and rewrite loop.

The deterministic citation validator accepted all 20 generated answers in both
the baseline and grader runs. The checker-only path marked 11 of 20 answers
unfaithful and returned low confidence for each. The full graph made 39 answer
attempts, received 25 unfaithful verdicts, rewrote the query 19 times, and still
ended low confidence for six scenarios.

The baseline has the best answer-level scores. The grader has almost the same
faithfulness and relevancy while improving the retrieved context metrics, but it
adds eight Flash calls per query. The full graph reaches more context, but its
extra steps reduce faithfulness and relevancy below the simple baseline.

This is a small, judge-based comparison, so it does not justify a silent default
switch. The next non-paid step is a hand audit of ten saved baseline and full
answers against their cited statute text. Until then, dense baseline is the
preferred production candidate and the checker-rewriter loop remains an
experimental safety path rather than a demonstrated quality improvement.

## Manual audit decision

The ten-answer statute audit is complete in
[manual-answer-audit.md](manual-answer-audit.md). It found five baseline passes
and five partial answers, against three full-graph passes, two partial answers,
and five generic low-confidence failures. One baseline answer misstated the
minimum sentence in BNS 314, so citation membership alone is not a guarantee
that every claim is right. The generator prompt and a key-free regression test
now preserve the BNS 314 bounds and mandatory fine in its context. The live
in-corpus branch now uses scope controls, exact-section lookup, dense retrieval,
generation, and deterministic citation validation. The full graph remains
available only for comparison.

## Claim-level audit of the grounded trace

On 2026-07-23 I audited the saved
`data/eval/ragas-grounded-final-50.jsonl` answers without regenerating them.
The audit used pinned paid `deepseek-v4-flash` with thinking disabled. It made
100 successful calls, two per scenario, and used 485,761 input tokens plus
42,372 output tokens.

| audit metric | result |
|---|---:|
| scenarios | 50 |
| extracted claims | 215 |
| valid judge verdicts | 214 |
| invalid judge verdicts | 1 |
| supported valid claims | 212 |
| claim-support ratio | 0.991 |
| wrong punishment | 1 |
| missing condition | 1 |

The invalid verdict had a false `supported` boolean but a reason that explicitly
said the claim matched the statute. The audit excludes that item from both the
numerator and denominator and preserves the raw finding for inspection.

The two valid failures were `s09`, which flattened BNS Section 61's conditional
abetment punishment into a ten-year robbery maximum, and `s11`, which incorrectly
said the BNS Section 124 acid offence was listed as compoundable under BNSS
Section 359. Both answers had the relevant retrieved law, so these are generation
errors rather than retrieval misses.

This claim-support ratio is not directly comparable with the 0.591 RAGAS
faithfulness score. It uses a separate claim decomposition prompt, restored
statute labels, exact answer spans, and evidence-linked verdicts. The large gap
shows that evaluator behavior is part of the plateau diagnosis. It does not
justify replacing the fixed RAGAS release metric without a separate validation
study.

### Two-case generation repair

I then regenerated only the two confirmed failures, `s09` and `s11`, after
adding narrow rules for cross-referenced punishments and closed statutory
tables. Both final answers used Mistral Small for routing and NVIDIA Nemotron 3
Ultra for generation, with no paid answer fallback. Mistral used 3,113 input
and 24 output tokens; Nemotron used 12,373 input and 496 output tokens.

The pinned paid `deepseek-v4-flash` claim audit supported all eight extracted
claims. Its four calls used 20,330 input and 1,929 output tokens.

On a matched RAGAS rerun of only those two saved cases, faithfulness rose from
**0.639 to 0.807** and answer relevancy rose from **0.722 to 0.771**. Context
precision moved from 0.614 to 0.590, while context recall stayed at 1.000. Each
pass made 39 successful DeepSeek calls. The baseline used 67,702 input and
4,727 output tokens; the repaired pass used 67,815 input and 5,033 output
tokens. This is a targeted gate, not a new 50-scenario headline result.

### Full claim-guard run

I regenerated all `s01-s50` answers after the two narrow prompt changes. The
run used the production graph, dense retrieval, no reranker, and the
1,155-chunk index. All 50 rows were high confidence, none were empty, every row
had citations, and six drafts used bounded citation repair. Average answer
length was 102.7 words.

One row, `s44`, ended mid-sentence. A same-settings retry produced the same
incomplete answer, so I kept the original row in the release sample instead of
editing or selectively replacing it. The retry used one Mistral call with
2,556 input and 12 output tokens, plus two NVIDIA calls with 14,448 input and
670 output tokens.

Provider logs for answer collection recorded 56 successful Mistral Small calls
with 62,062 input and 1,821 output tokens. NVIDIA Nemotron 3 Ultra recorded 47
successes and two 503 responses, with 277,089 input and 11,818 output tokens on
successful calls. Paid DeepSeek V4 Pro recorded 11 successful fallback or
structured-output calls, using 56,106 input and 4,421 output tokens.

The judge-only pass reused
`data/eval/ragas-faithfulness-final-50.jsonl`. Pinned paid
`deepseek-v4-flash` ran with thinking disabled, two workers, two retries, and a
4,096-token ceiling. All 200 metric jobs completed. Its internal requests and
structured-output retries produced 856 successful DeepSeek calls, using
1,721,961 input and 135,528 output tokens. Three proxy 524 attempts failed and
recovered within the fixed retry settings.

| difficulty | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| easy (19) | 0.537 | 0.701 | 0.632 | 0.982 |
| medium (24) | 0.557 | 0.668 | 0.588 | 0.990 |
| hard (7) | 0.510 | 0.715 | 0.713 | 1.000 |
| **overall (50)** | **0.543** | **0.687** | **0.622** | **0.988** |

Against the previous grounded trace, faithfulness fell by 0.048. Answer
relevancy improved by 0.022, context precision by 0.015, and context recall by
0.036. The two-case faithfulness gain did not generalize to the full set. This
is the current-code headline result; the 0.807 score remains a two-case
diagnostic.
