# RAGAS results

First full run over the 50 hand-labelled scenarios in `data/eval/scenarios.jsonl`
(19 easy, 24 medium, 7 hard). These are diagnostics, not production-accuracy claims.
Model provenance is part of each result.

## Setup

- Agent: the full self-correcting graph (router, intent expander, grader, checker,
  rewrite loop). DeepSeek V4 Flash for control, DeepSeek V4 Pro for the answer.
- Judge: DeepSeek V4 Flash, temperature 0.
- Answer-relevancy embeddings: local `BAAI/bge-small-en-v1.5`.
- Corpus: the 1,151-chunk local BNS/BNSS/BSA index.

## Full-graph scores

| pipeline / retrieval | faithfulness | answer relevancy | context precision | context recall |
|---|---:|---:|---:|---:|
| full graph, dense, no reranker | 0.309 | 0.518 | 0.700 | 0.840 |
| full graph, hybrid RRF + reranker | 0.314 | 0.386 | 0.709 | 0.732 |

Faithfulness is rough (~0.31), and a lot of scenarios end in a canned low-confidence
reply after the checker rejects an answer the deterministic citation check already
accepted. The checker-to-rewriter loop changes the query, usually retrieves similar
text, and fails again. Something feels off with all this machinery — next step is to
actually measure whether the extra nodes earn their place.
