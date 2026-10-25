"""Explicit secondary analyses; never alter the primary reproduction cohort."""
from __future__ import annotations

import numpy as np
import pandas as pd
from irrCAC.raw import CAC
from sklearn.metrics import matthews_corrcoef

from .core import align, evaluate
from .metrics import LABELS, METRICS, encode


def preliminary_contrasts(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """N50, LLM claims, four Llama/R1 models, two EHR fact representations.

    Summaries equally weight eight model/fact combinations; descriptive, not a
    claim that the publication used this aggregation to select its settings.
    """
    subset = metrics.loc[(metrics.author_type == "llm") & (metrics.proposition_type == "claim") &
                         (metrics.top_n.astype(str) == "50") & metrics.model.isin(["R1-8B", "R1-70B", "Llama-8B", "Llama-70B"])]
    defaults = {"retrieval_method": "rerank", "reference_format": "absolute_time", "reference_only_admission": "True"}
    contrasts, summaries = [], []
    for axis in defaults:
        selected = subset.copy()
        for key, value in defaults.items():
            if key != axis:
                selected = selected.loc[selected[key].astype(str) == value]
        for (model, fact), group in selected.groupby(["model", "fact_type"], sort=True):
            reference = group.loc[group[axis].astype(str) == defaults[axis]].iloc[0]
            for row in group.to_dict("records"):
                if row["evaluated_cohort_sha256"] != reference["evaluated_cohort_sha256"]:
                    raise ValueError("Preliminary contrast cohorts differ")
                contrasts.append(dict(axis=axis, alternative_value=str(row[axis]), chosen_value=defaults[axis],
                                      model=model, fact_type=fact, n=int(row["evaluated_n"]),
                                      alternative_rater=row["rater_alias"], chosen_rater=reference["rater_alias"],
                                      **{f"chosen_minus_alternative_{k}": float(reference[k] - row[k]) for k in METRICS}))
        for value, group in selected.groupby(axis, sort=True):
            summaries.append(dict(axis=axis, value=str(value), configurations=len(group),
                                  aggregation="equal mean of four models x two fact types, N50, llm claim; descriptive only",
                                  **{k: float(group[k].mean()) for k in METRICS}))
    return pd.DataFrame(contrasts), pd.DataFrame(summaries)


def model_contrasts(endpoint_records: list, targets: dict) -> list[dict]:
    """p9 text numbers compared under the explicit scenario in author script 9a.

    Also expose subtraction AFTER rounding individual off-diagonal cells to 0.1
    percentage point (how the author plot formats cells). This is a diagnostic,
    not proof that the published text was calculated in that way.
    """
    by_model = {cfg["model"]: (cohort, pred) for cfg, cohort, pred, _ in endpoint_records if cfg["author_type"] == "llm" and
                cfg["proposition_type"] == "claim" and cfg["fact_type"] == "sentence" and cfg["top_n"] == "100"}
    rows = []
    pairs = [("Llama-70B", "Llama-8B"), ("R1-70B", "R1-8B"), ("R1-8B", "Llama-8B"), ("R1-70B", "Llama-70B")]
    paper_values = targets["model_improvement_percentage_points"]
    for (candidate, baseline), target in zip(pairs, paper_values, strict=True):
        cohort, pred = by_model[candidate]
        included, p, _ = align(cohort, pred)
        other, b, _ = align(cohort, by_model[baseline][1])
        if included != other:
            raise ValueError("Model contrast ID mismatch")
        true = np.array([r["human_gt"] for r in cohort])
        c_correct, b_correct = np.array(p) == true, np.array(b) == true
        gain, loss = int(np.sum(c_correct & ~b_correct)), int(np.sum(~c_correct & b_correct))
        net = (gain - loss) / len(cohort) * 100
        rounded_cells = round(gain / len(cohort) * 100, 1) - round(loss / len(cohort) * 100, 1)
        rows.append(dict(candidate=candidate, baseline=baseline, author_type="llm", proposition_type="claim", fact_type="sentence", top_n=100,
                         n=len(cohort), candidate_only_correct=gain, baseline_only_correct=loss,
                         exact_net_gain_percentage_points=net, paper_percentage_points=target,
                         matches_exact_at_display_precision=abs(net - target) < .05 + 1e-12,
                         separately_rounded_cells_difference_percentage_points=rounded_cells,
                         rounded_cell_difference_matches_paper=abs(rounded_cells - target) < 1e-12,
                         attribution="scope from author 9a; rounding explanation is an inference; formal Figure S11 unavailable"))
    return rows


def independent_ci_checks(cohort: list[dict], pred: list[dict], iterations: int) -> list[dict]:
    """Cross-check actual R1-70B data against sklearn, including every MCC draw.

    Predefined diagnostics only: raw CSV order; ID order from author script 5;
    valid-only CSV order. No search over seeds, subgroups or permutations.
    """
    variants = [("all_human_csv_order", cohort),
                ("all_proposition_id_order", sorted(cohort, key=lambda r: r["proposition_id"])),
                ("valid_only_human_csv_order", [r for r in cohort if r["invalid"] == "False"])]
    rows = []
    for name, selected in variants:
        ids = {r["proposition_id"] for r in selected}
        predictions = [r for r in pred if r["proposition_id"] in ids]
        aligned, predicted, _ = align(selected, predictions)
        true = pd.Series(encode([r["human_gt"] for r in aligned]))
        predicted_series = pd.Series(encode(predicted))
        result = evaluate(selected, predictions, profile="paper_item", iterations=iterations)
        independent_point = float(matthews_corrcoef(true, predicted_series))
        draws = [matthews_corrcoef(true.sample(frac=1, replace=True, random_state=i),
                                  predicted_series.sample(frac=1, replace=True, random_state=i)) for i in range(iterations)]
        independent_ci = np.percentile(draws, [2.5, 97.5])
        independent_ac1 = CAC(pd.DataFrame({"truth": true, "predicted": predicted_series}), categories=[0, 1, 2]).gwet()["est"]["coefficient_value"]
        ci = result["confidence_intervals"]["mcc"]
        matched = (abs(independent_point - result["mcc"]) < 1e-12 and np.allclose(ci, independent_ci, atol=1e-12, rtol=0) and
                   abs(round(result["gwet_ac1"], 5) - independent_ac1) < 1e-12)
        if not matched:
            raise ValueError("Actual-data independent metric validation failed")
        rows.append(dict(variant=name, n=len(selected), cohort_sha256=result["coverage"]["evaluated_cohort_sha256"],
                         mcc=result["mcc"], ci_lower=ci[0], ci_upper=ci[1], independent_sklearn_point=independent_point,
                         independent_sklearn_ci_lower=float(independent_ci[0]), independent_sklearn_ci_upper=float(independent_ci[1]),
                         independent_irrcac_ac1=float(independent_ac1), all_library_checks_pass=matched,
                         bootstrap_iterations=iterations))
    return rows
