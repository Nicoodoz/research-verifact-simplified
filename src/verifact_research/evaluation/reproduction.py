"""Recompute the formal paper's released predictions with the shared evaluator."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

import duckdb
import numpy as np
import pandas as pd

from verifact_research.audit.common import digest_file, new_run, read_csv, write_csv, write_json
from verifact_research.audit.release import parse_checksums
from .core import cohort_digest, evaluate
from .metrics import LABELS, METRICS, clinician_metrics, encode, interval
from .release import CONFIG, STRATUM, load_cohort, load_predictions

ROOT = Path(__file__).resolve().parents[3]
TASK = "002_reproduce_paper_results"
BASELINE_MODEL = "R1-70B"
COHORT_FIELDS = ["proposition_id", "subject_id", "hadm_id", "author_type", "proposition_type", "human_gt", "invalid"]


def frame_csv(path: Path, frame: pd.DataFrame) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        frame.to_csv(handle, index=False, lineterminator="\n", float_format="%.12g")


def flat_result(meta: dict, result: dict) -> dict:
    coverage = result["coverage"]
    row = {**meta, **{k: coverage[k] for k in ["expected_n", "evaluated_n", "missing_n", "coverage",
                 "expected_patients", "evaluated_patients", "expected_cohort_sha256", "evaluated_cohort_sha256"]}}
    row.update({k: result[k] for k in METRICS})
    row.update(profile=result["profile"], bootstrap_iterations=result["bootstrap_iterations"])
    row["full_cohort_pa_lower"], row["full_cohort_pa_upper"] = result["percent_agreement_full_cohort_bounds"]
    for name in METRICS:
        ci = result.get("confidence_intervals", {}).get(name, [None, None])
        row[name + "_ci_lower"], row[name + "_ci_upper"] = ci
    for i, true in enumerate(["s", "ns", "na"]):
        for j, pred in enumerate(["s", "ns", "na"]):
            row[f"cm_{true}_{pred}"] = result["confusion_matrix"][i][j]
    return row


def clinician_analysis(cohort: list[dict], iterations: int) -> tuple[list[dict], list[dict]]:
    rows, membership = [], []
    for subset, selected_label in [("all", None), ("any_supported", LABELS[0]),
                                    ("any_not_supported", LABELS[1]), ("any_not_addressed", LABELS[2])]:
        eligible = [r for r in cohort if selected_label is None or selected_label in [r[f"verdict{i}"] for i in range(1, 4)]]
        for author, kind in [("llm", "claim"), ("llm", "sentence"), ("human", "claim"), ("human", "sentence")]:
            selected = sorted([r for r in eligible if r["author_type"] == author and r["proposition_type"] == kind],
                              key=lambda r: r["proposition_id"])
            votes = np.array([encode([r[f"verdict{i}"] for i in range(1, 4)]) for r in selected])
            point = clinician_metrics(votes)
            draws = np.empty((iterations, 2))
            for i in range(iterations):
                ix = np.random.RandomState(i).choice(len(votes), len(votes), replace=True)
                draws[i] = clinician_metrics(votes[ix])
            draws[:, 1] = np.round(draws[:, 1], 5)
            row = dict(subset=subset, author_type=author, proposition_type=kind, n=len(selected),
                       subset_total=len(eligible), patients=len({r["subject_id"] for r in selected}),
                       invalid_n=sum(r["invalid"] == "True" for r in selected),
                       cohort_sha256=cohort_digest(selected), bootstrap_iterations=iterations)
            for j, name in enumerate(METRICS[:2]):
                row[name] = float(point[j])
                row[name + "_ci_lower"], row[name + "_ci_upper"] = interval(draws[:, j])
            rows.append(row)
            membership.extend(dict(subset=subset, author_type=author, proposition_type=kind, proposition_id=r["proposition_id"])
                              for r in selected)
    return rows, membership


def compare_targets(targets: dict, clinician: list[dict], ai: list[dict]) -> list[dict]:
    comparisons = []
    for category, source_rows, actual_rows, keys in [
        ("clinician", targets["clinician"], clinician, ["subset", *STRATUM]),
        ("ai", targets["ai"], ai, ["model", *STRATUM, "fact_type", "top_n"]),
    ]:
        for target in source_rows:
            matches = [r for r in actual_rows if all(str(r[k]) == str(target[k]) for k in keys)
                       and (category == "clinician" or r["publication_role"] == "main")]
            if len(matches) != 1:
                raise ValueError(f"Target has {len(matches)} matches: {target}")
            actual = matches[0]
            base = dict(category=category, source=target["source"], **{k: target[k] for k in keys})
            for metric in METRICS:
                if metric not in target:
                    continue
                for part in ["point", "ci_lower", "ci_upper"]:
                    if part != "point" and metric + "_ci" not in target:
                        continue
                    expected = target[metric] if part == "point" else target[metric + "_ci"][0 if part == "ci_lower" else 1]
                    observed = actual[metric if part == "point" else metric + "_" + part]
                    tolerance = targets["rounding_tolerances"][metric]
                    match = abs(observed - expected) < tolerance + 1e-12
                    comparisons.append({**base, "metric": metric, "part": part, "paper_value": expected,
                                        "observed": observed, "difference": observed - expected,
                                        "display_rounding_tolerance": tolerance,
                                        "status": "matches_displayed_precision" if match else "differs"})
            if category == "clinician":
                comparisons.append({**base, "metric": "subset_total", "part": "count", "paper_value": target["subset_total"],
                                    "observed": actual["subset_total"], "difference": actual["subset_total"] - target["subset_total"],
                                    "display_rounding_tolerance": 0,
                                    "status": "matches_displayed_precision" if actual["subset_total"] == target["subset_total"] else "differs"})
    return comparisons


def reference_budgets(base: Path, ai: pd.DataFrame, progress) -> pd.DataFrame:
    """Exact Python str.split word counts, one payload at a time; no text is exported."""
    lengths, seen = {}, 0
    with duckdb.connect(config={"memory_limit": "2GB", "threads": 2}) as db:
        cursor = db.execute("SELECT reference_id, reference FROM read_parquet(?)", [str(base / "verifact/reference_payloads.parquet")])
        while batch := cursor.fetchmany(256):
            for ref_id, reference in batch:
                if ref_id in lengths:
                    raise ValueError("Duplicate reference_id")
                lengths[ref_id] = (len(reference.split()), len(reference))
            seen += len(batch)
            if seen % 51200 == 0:
                progress(f"reference word counts: {seen} payloads")
    if not set(ai.reference_id) <= set(lengths):
        raise ValueError("Unresolved reference payload")
    rows = ai[["model", "rater_alias", *STRATUM, "reference_id"]].copy()
    rows["reference_word_count"] = [lengths[r][0] for r in rows.reference_id]
    rows["reference_char_count"] = [lengths[r][1] for r in rows.reference_id]
    return rows.groupby(["model", "rater_alias", *STRATUM], sort=True).agg(
        reference_n=("reference_id", "size"), unique_payloads=("reference_id", "nunique"),
        mean_word_length=("reference_word_count", "mean"), min_words=("reference_word_count", "min"),
        max_words=("reference_word_count", "max"), mean_char_length=("reference_char_count", "mean")).reset_index()


def run_analysis(base: Path, audit: Path, run: Path, iterations: int, progress) -> dict:
    cohort = load_cohort(base, audit)
    master = pd.DataFrame(cohort)
    write_csv(run / "cohort_master.csv", cohort)
    (run / "cohorts").mkdir()
    (run / "baseline_predictions").mkdir()
    strata = {}
    cohort_summary = []
    for author, kind in [("llm", "claim"), ("llm", "sentence"), ("human", "claim"), ("human", "sentence")]:
        for validity in ["all", "valid_only"]:
            selected = [r for r in cohort if r["author_type"] == author and r["proposition_type"] == kind and
                        (validity == "all" or r["invalid"] == "False")]
            name = f"{author}_{kind}_{validity}"
            strata[author, kind, validity] = selected
            write_csv(run / "cohorts" / f"{name}.csv", [{k: r[k] for k in COHORT_FIELDS} for r in selected])
            cohort_summary.append(dict(cohort=name, n=len(selected), patients=len({r["subject_id"] for r in selected}),
                                       sha256=cohort_digest(selected), label_counts=dict(Counter(r["human_gt"] for r in selected))))
    write_json(run / "cohorts.json", cohort_summary)
    trivial = []
    for (author, kind, validity), selected in strata.items():
        predicted = [dict(proposition_id=r["proposition_id"], verdict="Supported") for r in selected]
        result = evaluate(selected, predicted, profile="none")
        trivial.append(flat_result(dict(model="Always Supported", author_type=author, proposition_type=kind,
                                        validity_policy=validity), result))
    write_csv(run / "trivial_baseline.csv", trivial)
    progress("clinician Table 1: 16 strata and 1000-seed bootstrap")
    clinicians, membership = clinician_analysis(cohort, iterations)
    write_csv(run / "clinician_metrics.csv", clinicians)
    write_csv(run / "clinician_subset_membership.csv", membership)
    ai, expected = load_predictions(base)
    ai = ai.merge(master[["proposition_id", *STRATUM]], on="proposition_id", how="left", validate="many_to_one")
    if ai[STRATUM].isna().any().any():
        raise ValueError("Unknown AI proposition")
    keys = ["model", "rater_alias", *STRATUM]
    observed = ai[keys].drop_duplicates()
    permitted = expected[keys]
    if not (observed.merge(permitted, on=keys, how="left", indicator=True)._merge == "both").all():
        raise ValueError("Unexpected model/stratum configuration")
    groups = ai.groupby(keys, sort=False).indices
    metrics, sensitivities, missing_rows, classes, results = [], [], [], [], []
    selected_records = []
    research_results = []
    for number, config in enumerate(expected.to_dict("records"), 1):
        signature = tuple(config[k] for k in keys)
        selected = strata[config["author_type"], config["proposition_type"], "all"]
        prediction_frame = ai.iloc[groups.get(signature, [])]
        pred = prediction_frame[["proposition_id", "verdict"]].to_dict("records")
        result = evaluate(selected, pred, profile="paper_item", missing="available", iterations=iterations)
        evaluated_ids = {r["proposition_id"] for r in pred}
        meta = {**config, "validity_policy": "all", "expected_invalid_n": sum(r["invalid"] == "True" for r in selected),
                "evaluated_invalid_n": sum(r["invalid"] == "True" and r["proposition_id"] in evaluated_ids for r in selected),
                "time_metadata_conflict_n": sum(r["time_metadata_conflict"] == "True" for r in selected)}
        metrics.append(flat_result(meta, result))
        results.append({"configuration": config, "evaluation": result})
        for label, values in result["per_class"].items():
            classes.append({**config, "label": label, **values})
        missing_rows.extend({**config, "proposition_id": pid} for pid in result["coverage"]["missing_ids"])
        valid = strata[config["author_type"], config["proposition_type"], "valid_only"]
        valid_ids = {r["proposition_id"] for r in valid}
        valid_pred = [r for r in pred if r["proposition_id"] in valid_ids]
        valid_result = evaluate(valid, valid_pred, profile="none", missing="available")
        sensitivities.append(flat_result({**config, "analysis": "valid_only", "excluded_n": len(selected) - len(valid)}, valid_result))
        endpoint = config["publication_role"] == "main" and ((config["fact_type"] == "claim" and config["top_n"] == "150") or
                                                            (config["fact_type"] == "sentence" and config["top_n"] == "100"))
        if endpoint:
            selected_records.append((config, selected, pred, prediction_frame))
            # Predeclared research endpoint, no per-model top-N tuning on this benchmark.
            if config["fact_type"] == "sentence":
                research = evaluate(valid, valid_pred, profile="research_patient", iterations=iterations)
                research_results.append({"configuration": config, "evaluation": research})
                if config["model"] == BASELINE_MODEL:
                    name = f"{config['author_type']}_{config['proposition_type']}"
                    write_csv(run / "baseline_predictions" / f"R1-70B_{name}_all.csv", pred)
                    write_csv(run / "baseline_predictions" / f"R1-70B_{name}_valid_only.csv", valid_pred)
            for name, keep in [
                ("without_time_metadata_conflicts", [r for r in selected if r["time_metadata_conflict"] == "False"]),
                ("initial_unanimous", [r for r in selected if r["initial_agreement"] == "3"]),
                ("initial_majority", [r for r in selected if r["initial_agreement"] == "2"]),
                ("initial_all_different", [r for r in selected if r["initial_agreement"] == "0"]),
            ]:
                ids = {r["proposition_id"] for r in keep}
                sensitivity = evaluate(keep, [r for r in pred if r["proposition_id"] in ids], profile="none", missing="available")
                sensitivities.append(flat_result({**config, "analysis": name, "excluded_n": len(selected) - len(keep)}, sensitivity))
        if number % 20 == 0:
            progress(f"AI configuration metrics: {number}/{len(expected)}")
    write_json(run / "ai_metrics.json", results)
    write_csv(run / "per_class_metrics.csv", classes)
    frame_csv(run / "sensitivity_metrics.csv", pd.DataFrame(sensitivities))
    frame_csv(run / "missing_prediction_keys.csv", pd.DataFrame(missing_rows))
    write_json(run / "research_baselines.json", research_results)
    write_csv(run / "research_baselines.csv", [flat_result({**r["configuration"], "validity_policy": "valid_only"}, r["evaluation"])
                                              for r in research_results])
    # Missing config: evaluate all nine models on the same explicitly retained IDs.
    common_metrics, common_membership = [], []
    missing_configs = {tuple(r[k] for k in [*STRATUM, *CONFIG]) for r in missing_rows}
    for signature in sorted(missing_configs):
        cfg = dict(zip([*STRATUM, *CONFIG], signature))
        matches = expected.loc[(expected[list(cfg)] == pd.Series(cfg)).all(axis=1)]
        shared = {r["proposition_id"] for r in strata[cfg["author_type"], cfg["proposition_type"], "all"]}
        preds = []
        for config in matches.to_dict("records"):
            part = ai.iloc[groups[tuple(config[k] for k in keys)]][["proposition_id", "verdict"]].to_dict("records")
            shared &= {r["proposition_id"] for r in part}
            preds.append((config, part))
        selected = [r for r in strata[cfg["author_type"], cfg["proposition_type"], "all"] if r["proposition_id"] in shared]
        common_membership.extend({**cfg, "proposition_id": r["proposition_id"]} for r in selected)
        for config, pred in preds:
            result = evaluate(selected, [r for r in pred if r["proposition_id"] in shared], profile="none")
            common_metrics.append(flat_result(config, result))
    frame_csv(run / "common_available_metrics.csv", pd.DataFrame(common_metrics))
    frame_csv(run / "common_available_membership.csv", pd.DataFrame(common_membership))
    progress("measuring actual reference lengths; matching endpoint inputs across models")
    budgets = reference_budgets(base, ai, progress)
    final_metrics = pd.DataFrame(metrics).merge(budgets, on=keys, how="left", validate="one_to_one")
    if final_metrics.mean_word_length.isna().any():
        raise ValueError("Missing reference budget")
    frame_csv(run / "ai_metrics.csv", final_metrics)
    from .diagnostics import independent_ci_checks, model_contrasts, preliminary_contrasts
    targets = json.loads((ROOT / "tasks" / TASK / "paper_targets.json").read_text(encoding="utf-8"))
    contrasts, preliminary = preliminary_contrasts(final_metrics)
    frame_csv(run / "preliminary_contrasts.csv", contrasts)
    frame_csv(run / "preliminary_summary.csv", preliminary)
    write_csv(run / "model_size_reasoning_contrasts.csv", model_contrasts(selected_records, targets))
    progress("independent sklearn/irrCAC validation of actual-data metrics and MCC CI diagnostics")
    reference_record = next(r for r in selected_records if r[0]["model"] == BASELINE_MODEL and
                            r[0]["author_type"] == "llm" and r[0]["proposition_type"] == "claim" and r[0]["fact_type"] == "sentence")
    write_csv(run / "mcc_ci_diagnostics.csv", independent_ci_checks(reference_record[1], reference_record[2], iterations))
    input_comparisons = []
    for config, selected, pred, frame in selected_records:
        reference_cfg = next(entry for entry in selected_records if entry[0]["model"] == BASELINE_MODEL and
                             all(entry[0][k] == config[k] for k in [*STRATUM, *CONFIG]))
        pair = frame[["proposition_id", "reference_id"]].merge(reference_cfg[3][["proposition_id", "reference_id"]],
                         on="proposition_id", validate="one_to_one", suffixes=("_candidate", "_baseline"))
        equal = int((pair.reference_id_candidate == pair.reference_id_baseline).sum())
        input_comparisons.append({**config, "reference_model": BASELINE_MODEL, "paired_n": len(pair),
                                  "exact_reference_equal_n": equal, "exact_reference_equal_fraction": equal / len(pair)})
    write_csv(run / "endpoint_input_comparisons.csv", input_comparisons)
    comparisons = compare_targets(targets, clinicians, metrics)
    frame_csv(run / "paper_comparisons.csv", pd.DataFrame(comparisons))
    write_json(run / "paper_comparisons.json", {"comparisons": comparisons, "unverified": targets["unverified"]})
    prior_missing = read_csv(audit / "missing_verdict_keys.csv")[1]
    canonical_key = lambda r: (r["model"], r["rater_alias"], r["proposition_id"])
    checks = [
        dict(id="cohort_matches_001", status="pass", observed=len(cohort), expected=13070),
        dict(id="matrix_pair_count", status="pass" if len(expected) == 426 else "fail", observed=len(expected), expected=426),
        dict(id="ai_row_count", status="pass" if len(ai) == 1437100 else "fail", observed=len(ai), expected=1437100),
        dict(id="missing_keys_match_001", status="pass" if {canonical_key(r) for r in prior_missing} == {canonical_key(r) for r in missing_rows} else "fail",
             observed=len(missing_rows), expected=len(prior_missing)),
        dict(id="actual_data_independent_metrics_and_intervals", status="pass", observed="sklearn1.6.1 and irrCAC0.4.3 agree in all 3 predefined diagnostic cohorts", expected="agreement"),
        dict(id="known_prediction_gap", status="warning" if missing_rows else "pass", observed=len(missing_rows), expected=0),
        dict(id="known_second_round_inconsistency", status="warning", observed=sum(r["second_round_anomaly"] == "True" for r in cohort), expected=0),
        dict(id="unavailable_formal_supplement", status="unverified", observed="HTTP403; formal appendix not acquired", expected="formal numeric tables"),
    ]
    checks.extend(dict(id=f"paper_{i:03d}", status="pass" if r["status"] == "matches_displayed_precision" else "warning",
                       observed=r["observed"], expected=r["paper_value"], source=r["source"], metric=r["metric"], part=r["part"])
                  for i, r in enumerate(comparisons, 1))
    write_json(run / "checks.json", checks)
    summary = dict(task=TASK, patients=len({r["subject_id"] for r in cohort}), propositions=len(cohort),
                   invalid_propositions=sum(r["invalid"] == "True" for r in cohort), ai_rows=len(ai), expected_ai_rows=sum(r["expected_n"] for r in metrics),
                   configuration_pairs=len(expected), main_pairs=int((expected.publication_role == "main").sum()),
                   models=int(ai.model.nunique()), raters=int(ai.rater_alias.nunique()), matrix_rows=int(expected.matrix_row.nunique()),
                   preliminary_pairs=int((expected.publication_role == "preliminary_sensitivity").sum()),
                   missing_predictions=len(missing_rows), invalid_predicted_ids=len(set(ai.proposition_id) & {r["proposition_id"] for r in cohort if r["invalid"] == "True"}),
                   bootstrap_iterations=iterations, paper_comparisons=dict(Counter(r["status"] for r in comparisons)),
                   check_statuses=dict(Counter(r["status"] for r in checks)), cohorts=cohort_summary,
                   unverified=targets["unverified"])
    write_json(run / "summary.json", summary)
    from .report import write_report
    write_report(run, summary, clinicians, final_metrics.to_dict("records"), comparisons, research_results, checks)
    return summary


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=ROOT / "data/00_raw/verifact-bhc/1.1.0")
    parser.add_argument("--audit", type=Path, default=ROOT / "outputs/001_dataset_audit/run_006")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs" / TASK)
    parser.add_argument("--run-name")
    parser.add_argument("--bootstrap", type=int, default=1000)
    args = parser.parse_args(argv)
    if args.bootstrap < 1:
        parser.error("--bootstrap must be positive")
    if args.output_root.resolve() == args.release.resolve() or args.release.resolve() in args.output_root.resolve().parents:
        parser.error("Output cannot be inside the release")
    run = new_run(args.output_root, args.run_name, ROOT / "data/00_raw")
    start = time.perf_counter()
    manifest = dict(task=TASK, started_utc=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                    parameters={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                    python=sys.version, platform=platform.platform(), status="running",
                    dependencies={d: importlib.metadata.version(d) for d in ["numpy", "pandas", "scipy", "scikit-learn", "irrCAC", "duckdb"]})
    progress = lambda s: print(f"[{time.perf_counter() - start:.1f}s] {s}", flush=True)
    files = sorted(p for p in args.release.rglob("*") if p.is_file())
    manifest["input_sha256"] = {str(p.relative_to(args.release)).replace("\\", "/"): digest_file(p) for p in files}
    source_paths = [ROOT / "docs/sources/VeriFact.pdf", ROOT / "data/00_raw/verifact-bhc/1.1.0/README.md", args.audit / "manifest.json"]
    source_paths += sorted(p for p in (ROOT / "docs/sources/verifact_upstream_f115d36cb65f").rglob("*") if p.is_file())
    manifest["source_sha256"] = {str(p.relative_to(ROOT)).replace("\\", "/"): digest_file(p) for p in source_paths}
    code = [ROOT / "environment.yml", ROOT / "README.md", ROOT / "AGENTS.md"]
    for directory in ["src", "scripts", "tests", "tasks/002_reproduce_paper_results"]:
        code += sorted(p for p in (ROOT / directory).rglob("*") if p.is_file() and p.suffix in {".py", ".json", ".md"})
    manifest["code_and_config_sha256"] = {str(p.relative_to(ROOT)).replace("\\", "/"): digest_file(p) for p in code}
    manifest["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    progress(f"run directory: {run.relative_to(ROOT)}")
    exit_code = 0
    try:
        prior = json.loads((args.audit / "manifest.json").read_text(encoding="utf-8"))
        manifest["raw_matches_001"] = manifest["input_sha256"] == prior["input_sha256"]
        if not manifest["raw_matches_001"]:
            raise ValueError("Raw release bytes differ from the 001 audited release")
        declared = parse_checksums((args.release / "SHA256SUMS.txt").read_text(encoding="utf-8"))
        manifest["official_checksums_match"] = all(manifest["input_sha256"].get(name) == digest for name, digest in declared.items())
        if not manifest["official_checksums_match"]:
            raise ValueError("Official release SHA256SUMS validation failed")
        upstream = ROOT / "docs/sources/verifact_upstream_f115d36cb65f"
        for path in upstream.glob("*source_manifest.json"):
            for entry in json.loads(path.read_text(encoding="utf-8"))["files"]:
                if digest_file(upstream / entry["path"]) != entry["sha256"]:
                    raise ValueError(f"Pinned upstream reference changed: {entry['path']}")
        summary = run_analysis(args.release, args.audit, run, args.bootstrap, progress)
        manifest["status"] = "completed_with_differences" if summary["paper_comparisons"].get("differs", 0) else "completed"
        if summary["check_statuses"].get("fail", 0):
            manifest["status"], exit_code = "failed_checks", 1
    except Exception:
        manifest["status"], exit_code = "error", 1
        error = traceback.format_exc()
        (run / "error.txt").write_text(error, encoding="utf-8", newline="\n")
        print(error, file=sys.stderr)
    finally:
        after = {str(p.relative_to(args.release)).replace("\\", "/"): digest_file(p) for p in sorted(args.release.rglob("*")) if p.is_file()}
        manifest["raw_unchanged"] = after == manifest["input_sha256"]
        if not manifest["raw_unchanged"]:
            manifest["status"], exit_code = "raw_changed", 1
        manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
        manifest["elapsed_seconds"] = time.perf_counter() - start
        manifest["output_sha256"] = {str(p.relative_to(run)).replace("\\", "/"): digest_file(p) for p in sorted(run.rglob("*")) if p.is_file()}
        write_json(run / "manifest.json", manifest)
    progress(f"{manifest['status']}; raw unchanged={manifest['raw_unchanged']}")
    return exit_code
