# 043：Targeted Evidence Utility for the Original Judge

## Question

039 identified 55 post-hoc R cases in which the original C48 did not pass the Qwen strict trace audit, but C48 plus additional same-admission EHR passages did. 043 does not develop a new retriever. It asks the missing causal-mechanism question:

> If the 039-cited additional passages are actually shown to the original DeepSeek scoring Judge, does the Judge itself move toward Supported and produce a reason that is semantically consistent and grounded?

This is a reserved-set post-hoc mechanism experiment. It is not a new unbiased performance estimate and cannot be used to reopen model selection.

## Cohort

Fixed cohort: the 55 cases satisfying all of:
- 036 U0 non-S → U2 Supported;
- doctor GT = Supported (R);
- 039 attribution = B_fullEHR_search_sufficient.

The cohort is outcome-conditioned by construction. This limitation is explicit.

## Three input conditions

For each claim, the ordinary 036 C48 is the base reference.

A — **C48 baseline**: original C48 unchanged.

B — **targeted evidence addition**: original C48 plus the unique EHR passages that were actually cited by the 039 Qwen evidence audit as supporting the claim. Original C48 is never deleted or replaced.

C — **matched additional-context control**: original C48 plus the same number of non-cited passages drawn from the same 039 high-recall external set. Each control passage is selected without using DeepSeek output by deterministic matching: prefer the same note category, then closest character length, then lower claim-token Jaccard overlap, then stable hash. Cited passages, exact duplicate text and original-C48 passage IDs are excluded.

B and C append numeric reference entries after the last original C48 entry. No GT, U2 label, 039 category, or old reason is sent to the Judge.
## Judge and repeats

All three conditions use the unchanged DeepSeek scoring Judge prompt/schema and model alias deepseek-v4-flash-0731.

Round 0: all 55 × 3 conditions.

Repeat diagnostic: 12 claims are fixed by hash before any new Judge result; A/B/C are independently called again as round 1. Repeats are a stability diagnostic, not independent samples.

HTTP200 answers are never rerun for answer quality.

## Primary mechanism outcomes

Because all 55 claims have doctor GT=Supported, the primary label outcome is the number predicted Supported by the original Judge itself:
- ordinary score verdict;
- U0 score argmax;
- fixed U2 label.

Primary paired contrasts:
- B vs A: does targeted evidence increase original-Judge Supported decisions?
- B vs C: is any change specific to targeted evidence rather than merely adding more context?

For each contrast report rescue (non-S→S), harm (S→non-S), net change, exact paired sign/McNemar-style binomial p-value as a descriptive statistic, and patient-level direction counts. The p-value is not treated as confirmatory because the cohort was post-hoc selected.

## Reason audit

After DeepSeek round-0 predictions are frozen, a separate Qwen audit receives only:
- claim;
- the exact condition reference;
- DeepSeek verdict, reason and checks;
- IDs of the appended reference entries, if any.

It does not receive GT, U0/U2, condition name, 039 attribution, or prior outputs.

Return:
- label_reason_alignment: consistent / contradictory / mixed;
- grounding: grounded / partial / ungrounded;
- added_evidence_material: yes / no / not_applicable;
- short explanation.

This is an automatic research audit, not clinician gold and not an independent replication of 039 because Qwen also supplied the original 039 evidence trace.
## Interpretation rules

A useful targeted-evidence mechanism requires more than a higher Supported rate:
1. B should show positive net Supported movement versus A;
2. B should outperform the matched-context control C in the same direction;
3. new Supported outputs should usually have consistent, grounded reasons;
4. repeat diagnostics should not show that the apparent effect is dominated by ordinary run-to-run flips.

If these conditions are not met, 039 evidence discovery cannot be assumed to be useful to the original Judge, and further retrieval optimization aimed specifically at these passages loses its direct mechanism justification.

If they are met, the next task may investigate how to recover such evidence automatically in the normal retrieval chain. 043 itself does not propose or validate that deployable retrieval method.

## Cost / integrity

Task API cap: CNY 35.

DeepSeek calls are research evaluation calls only. Qwen reason-audit calls are also research-only and do not add a deployment stage.

Existing 036/039 artifacts are read-only. Independent audit is separate from executor verification.
