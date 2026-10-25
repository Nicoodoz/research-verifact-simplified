# 042：Coverage-aware Evidence Packing

## Research question

039 showed that some claims can be supported by evidence outside the final C48 reference. A follow-up trace found that many such passages had already entered the original 48-candidate pool but were lost during final evidence packing. 042 tests whether a deterministic local selector can improve the finite evidence package without adding any deployment-time API stage.

## Deployment-chain constraint

The deployed chain remains unchanged:

EHR → existing BM25/dense retrieval → existing 48-candidate pool → existing BGE reranker → local evidence packing → existing DeepSeek scoring Judge.

042 adds no planner, query-expansion model, embedding call, rerank call, or second Judge call to the deployed system. Only the local evidence-packing algorithm changes.

## Data boundary

No reserved40 result is used for method selection or threshold tuning. The 039 reserved analysis is treated only as mechanism motivation.

Primary development material is the already consumed 031 development split:
- expansion: 12 patients, 998 claims;
- confirmation: 12 disjoint patients, 1148 claims.

042 is restricted to claims whose 031 run has native 48-candidate and frozen rerank information. This eligibility is determined before connecting GT:
- expansion eligible: 705 claims;
- confirmation eligible: 696 claims.

Cached legacy-C48 claims without a native 031 rerank trace are excluded from this first test rather than reconstructed from heterogeneous historical services.
## Fixed selectors

Baseline reproduces the original 031 C48 packing: rerank-descending greedy selection, exact duplicate removal, maximum 2 passages per note, maximum 16 passages, 8000 body characters.

Two new local selectors are screened:

1. **SoftNote**: identical greedy rerank order and the same 8000/16 limits, but the hard max-2-per-note rule is removed. Exact duplicate removal remains.

2. **CovMMR**: same 48 candidates, same frozen rerank scores, exact duplicate removal, 8000/16 limits. Greedy utility is fixed before any 042 GT evaluation:
   - 0.70 normalized rerank-rank relevance;
   - 0.20 weighted claim-token coverage;
   - 0.10 passage novelty;
   - soft same-note penalty of 0.05 for each already selected passage from that note beyond the first.
The top reranked passage is always seeded. Claim-token weights are inverse candidate-document-frequency within the 48 candidates. Novelty is one minus maximum token Jaccard similarity to an already selected passage.

No weights or limits are tuned using 039 reserved outcomes.

## Screening and confirmation

A deterministic patient/author-balanced hash sample of 240 eligible expansion claims is frozen before GT connection.

For changed references only, contemporaneous DeepSeek scoring-Judge calls are sent for:
- reproduced baseline;
- SoftNote;
- CovMMR.

Identical references share the same response. HTTP200 answers are not rerun for content.

The development screen is evaluated only after all screen predictions are frozen. A candidate proceeds only if, versus the contemporaneous baseline:
- net correct improvement ≥ 5/240;
- false-S increase ≤ 3;
- neither author subgroup has net correct < -2;
- and U2 final-vs-score-verdict mismatch count does not increase.
If both pass, the higher net-correct candidate proceeds; ties use lower false-S, then lower mismatch count, then the simpler SoftNote rule.

If no candidate passes, 042 stops and does not touch the confirmation patients.
If one selector passes, it is frozen without further tuning and tested on all 696 eligible confirmation claims. Confirmation uses contemporaneous baseline and selected method only, with identical-reference sharing.

Primary confirmation endpoints:
- Score_verdict, U0 and fixed U2 label accuracy;
- MCC, false-S and class recall;
- U2 final-label versus the new scoring Judge's own verdict mismatch count;
- reason-label structural conflict rate for U2 (final label differs from scoring verdict);
- reference change rate, selected passage count and character use.

U2 is recomputed exactly as in 035: log(max(score/100,1e-6)), add λ=2 to Supported, then argmax.

## Interpretation

042 can support a retrieval/packing improvement only if the fixed selector improves downstream Judge behavior on the held-out development confirmation patients. It cannot be called an external validation and cannot reset or re-open reserved40.

The 039 55-case set may be replayed only after the selector is frozen, as a post-hoc mechanism check; it cannot select weights, limits, or the winner.

## Cost and safety

Only new DeepSeek scoring-Judge calls are allowed. No new retrieval API stages are introduced. Task cost cap: CNY 45. Stop on interface/model mismatch, repeated systemic invalidity, or cap breach. Existing 031 and 039 artifacts are read-only.

Execution self-check and independent audit are separate. Completion of executor verification must not be described as independent audit.
