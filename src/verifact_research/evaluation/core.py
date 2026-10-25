"""Strict sample alignment and one evaluation path for every method."""
from __future__ import annotations

import hashlib
import json

import numpy as np

from .metrics import (METRICS, classification_metrics, encode, interval, item_bootstrap,
                      patient_bootstrap)


def cohort_digest(cohort: list[dict]) -> str:
    """Ordered identity/label/patient fingerprint; ordering matters for paper bootstrap."""
    content = [[r["proposition_id"], r["subject_id"], r["human_gt"]] for r in cohort]
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def align(cohort: list[dict], predictions: list[dict], missing: str = "error") -> tuple[list[dict], list[str], dict]:
    if missing not in {"error", "available"}:
        raise ValueError("missing must be 'error' or explicitly 'available'")
    if not cohort:
        raise ValueError("Empty evaluation cohort")
    for name, rows in (("cohort", cohort), ("predictions", predictions)):
        ids = [r["proposition_id"] for r in rows]
        if any(not isinstance(pid, str) or not pid.strip() for pid in ids) or len(ids) != len(set(ids)):
            raise ValueError(f"Blank or duplicate proposition_id in {name}")
    encode([r["human_gt"] for r in cohort])
    encode([r["verdict"] for r in predictions])
    if any(not r.get("subject_id") for r in cohort):
        raise ValueError("Every cohort row must have a subject_id")
    expected = {r["proposition_id"] for r in cohort}
    pred = {r["proposition_id"]: r["verdict"] for r in predictions}
    extra = sorted(set(pred) - expected)
    absent = sorted(expected - set(pred))
    if extra:
        raise ValueError(f"Out-of-cohort predictions ({len(extra)}): {extra[:3]}")
    if absent and missing == "error":
        raise ValueError(f"Missing predictions ({len(absent)}): {absent[:3]}")
    included = [r for r in cohort if r["proposition_id"] in pred]
    if not included:
        raise ValueError("No predictions available")
    coverage = dict(expected_n=len(cohort), evaluated_n=len(included), missing_n=len(absent),
                    coverage=len(included) / len(cohort), missing_ids=absent, missing_policy=missing,
                    expected_cohort_sha256=cohort_digest(cohort), evaluated_cohort_sha256=cohort_digest(included),
                    expected_patients=len({r["subject_id"] for r in cohort}),
                    evaluated_patients=len({r["subject_id"] for r in included}))
    return included, [pred[r["proposition_id"]] for r in included], coverage


def evaluate(cohort: list[dict], predictions: list[dict], *, profile: str = "research_patient",
             missing: str = "error", iterations: int = 1000) -> dict:
    """Evaluate exactly the caller's explicit cohort; never silently filter invalid rows.

    paper_item: author's fixed seed item resampling. PA/AC1 sorted by ID; MCC
    in the input cohort order (release human_verdicts CSV order for reproduction).
    research_patient: same three point estimates; clustered CIs, sorted patient IDs.
    none: point estimates only. Use separate explicit cohort CSVs for invalid policy.
    """
    if profile not in {"paper_item", "research_patient", "none"}:
        raise ValueError("Unknown evaluation profile")
    rows, predicted, coverage = align(cohort, predictions, missing)
    truth = [r["human_gt"] for r in rows]
    result = classification_metrics(truth, predicted)
    correct = int(np.sum(np.array(truth) == np.array(predicted)))
    result["percent_agreement_full_cohort_bounds"] = [correct / coverage["expected_n"],
        (correct + coverage["missing_n"]) / coverage["expected_n"]]
    result.update(coverage=coverage, profile=profile, bootstrap_iterations=iterations if profile != "none" else 0,
                  bootstrap_seeds="0..iterations-1; numpy RandomState", confidence_level=.95,
                  weighting="micro (each proposition equal)", label_space="nominal fixed 3 categories")
    codes = 3 * encode(truth) + encode(predicted)
    if profile == "paper_item":
        draws = item_bootstrap(codes, iterations)
        order = np.argsort([r["proposition_id"] for r in rows])
        agreement_draws = item_bootstrap(codes[order], iterations)
        draws[:, :2] = agreement_draws[:, :2]
        # The author's irrCAC 0.4.3 returns AC1 rounded to five decimals per draw.
        draws[:, 1] = np.round(draws[:, 1], 5)
        result["sample_order"] = "PA/AC1: proposition_id lexical; MCC: supplied cohort order"
    elif profile == "research_patient":
        draws = patient_bootstrap(codes, [r["subject_id"] for r in rows], iterations)
        result["sample_order"] = "lexically sorted patient IDs; all propositions retained per sampled patient"
    else:
        return result
    result["confidence_intervals"] = {name: interval(draws[:, i]) for i, name in enumerate(METRICS)}
    return result


def paired_compare(cohort: list[dict], baseline: list[dict], candidate: list[dict], *, iterations: int = 1000) -> dict:
    """Candidate minus baseline, on identical complete IDs and paired patient draws."""
    rows, bpred, coverage = align(cohort, baseline)
    _, cpred, other = align(cohort, candidate)
    if coverage != other:
        raise ValueError("Paired comparison requires identical coverage")
    truth = encode([r["human_gt"] for r in rows])
    subjects = [r["subject_id"] for r in rows]
    bd = patient_bootstrap(3 * truth + encode(bpred), subjects, iterations)
    cd = patient_bootstrap(3 * truth + encode(cpred), subjects, iterations)
    bm = classification_metrics([r["human_gt"] for r in rows], bpred)
    cm = classification_metrics([r["human_gt"] for r in rows], cpred)
    return dict(direction="candidate minus baseline", coverage=coverage, bootstrap_iterations=iterations,
                resampling="paired patients, seeds 0..iterations-1", metrics={
                    name: dict(delta=cm[name] - bm[name], ci95=interval((cd - bd)[:, i]))
                    for i, name in enumerate(METRICS)})
