# RAGAS judge noise floor

Every recent architecture change moved the headline faithfulness score by less
than 0.05: grounded answers were +0.074, then the claim guards were -0.048, with
the other three metrics drifting in the opposite direction. Before chasing
another prompt edit, I wanted to know how much of that movement is real and how
much is just the judge scoring the same answers differently each time.

## Method

The study is judge-only. It reads one frozen answer trace and re-scores it, so no
answer is regenerated and only the evaluator path varies between passes. That
isolates evaluator noise from generator noise, which is the whole point. It also
matches the project's evaluation cost rule: never regenerate answers just because the
judge settings changed.

- Trace: `data/eval/ragas-grounded-final-50.jsonl` (the grounded-answer headline,
  50 scenarios).
- Metric: faithfulness only. It is the metric that plateaued, and restricting the
  set skips the context metrics' judge calls, cutting cost roughly 4x per pass.
- Judge: the pinned release judge (paid DeepSeek V4 Flash), thinking disabled.
- Repeats: 3.

Command:

```bash
uv run python -m src.eval.ragas_eval \
  --samples-in data/eval/ragas-grounded-final-50.jsonl \
  --metrics faithfulness \
  --repeat 3 \
  --scores-out data/eval/noise-floor-faithfulness.json
```

## Result

Ran 2026-07-24 on the pinned paid DeepSeek Flash release judge
(`ragas-judge-release`), thinking disabled, through the local OmniRoute gateway.
Three judge-only passes over the frozen grounded trace, faithfulness only.

| metric | mean | std | per-run values |
|---|---:|---:|---|
| faithfulness | 0.569 | 0.029 | 0.543, 0.565, 0.600 |

The same 50 answers, judged three times, scored 0.543 / 0.565 / 0.600, a spread
of 0.057 with a sample std of 0.029.

## Reading

These three passes show that single-pass judge variation is large enough to cover
the recent score changes:

- The claim-guard run scored 0.543 faithfulness, identical to one of the three
  values this study produced from the unchanged trace.
- The grounded run scored 0.591, inside the 0.543 to 0.600 re-judge range.
- The documented 0.048 grounded→claim-guard "regression" is smaller than the
  0.057 spread a single re-judge of the unchanged grounded trace produces.

At n=50 with a single judge pass, the recent prompt variants are not
distinguishable from judge noise. Read against the 0.991 independent
claim-support audit, the answers are already well grounded and the headline
metric can no longer resolve further improvement. Next steps, in order of value:
report faithfulness with this error bar, raise self-consistency (strictness > 1)
to shrink it, and promote the claim-level audit to a co-headline with a small
validation study instead of spending more iterations inside the noise band.
