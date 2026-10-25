"""Evaluate 068 repeats and pre-outcome signals without selecting a new method."""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/068_final_pack_utility_diagnosis"
P067 = ROOT / "outputs/067_conservative_evidence_packing"
sys.path.insert(0, str(ROOT / "tasks/067_conservative_evidence_packing"))
import common067 as c  # noqa: E402
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))
import core024  # noqa: E402
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.evaluation import evaluate, paired_compare  # noqa: E402


def jsonl(path):
    return [json.loads(line) for line in path.open(encoding="utf-8-sig") if line.strip()]


def save(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def metric_rows(rows, key):
    return [{"proposition_id": row["id"], "verdict": row[key]} for row in rows]


def false_s(rows, key):
    return sum(row["GT"] != "Supported" and row[key] == "Supported" for row in rows)


def load_receipts(jobs):
    by_id = {}
    for job in jobs:
        rid = job["request_id"]
        folder = OUT / "attempts" / (c.digest(rid)[:24] + "_01")
        # Attempt directory names use SHA-256 of request_id, equivalent to c.digest only for JSON strings.
        import hashlib
        folder = OUT / "attempts" / (hashlib.sha256(rid.encode()).hexdigest()[:24] + "_01")
        receipt = folder / "receipt.json"
        if not receipt.exists():
            by_id[rid] = {"status": "not_sent_or_missing"}
            continue
        rec = json.loads(receipt.read_text(encoding="utf-8"))
        transport = rec["transport"]
        if transport.get("http_status") != 200:
            by_id[rid] = {"status": "non200_or_unknown", "http_status": transport.get("http_status")}
            continue
        parsed = core024.parse(transport, True)
        valid = parsed.get("status") in ("valid", "valid_with_format_anomaly") and parsed.get("verdict") in c.LABELS and parsed.get("scores")
        if valid:
            by_id[rid] = {"status": "valid", "raw": parsed["verdict"], "pg": c.priorg(parsed["scores"]), "scores": parsed["scores"], "model_returned": parsed.get("model_returned")}
        else:
            by_id[rid] = {"status": "invalid_prediction", "parse_status": parsed.get("status"), "errors": parsed.get("errors", [])}
    return by_id


def auc(y, values):
    if len(set(y)) < 2:
        return None
    positive = [values[i] for i in range(len(y)) if y[i] == 1]
    negative = [values[i] for i in range(len(y)) if y[i] == 0]
    return float(sum((a > b) + 0.5 * (a == b) for a in positive for b in negative) / (len(positive) * len(negative)))


def patient_auc_ci(rows, feature, direction, iterations=1000):
    scores = [float(row[feature]) * direction for row in rows]
    labels = [int(row["group"] == "rescue") for row in rows]
    point = auc(labels, scores)
    sids = sorted({row["sid"] for row in rows})
    by_sid = defaultdict(list)
    for index, row in enumerate(rows):
        by_sid[row["sid"]].append(index)
    rng = np.random.default_rng(20260923068)
    draws = []
    for _ in range(iterations):
        sampled = rng.choice(sids, len(sids), replace=True)
        indices = [i for sid in sampled for i in by_sid[str(sid)]]
        result = auc([labels[i] for i in indices], [scores[i] for i in indices])
        if result is not None:
            draws.append(result)
    return {"auc_rescue_vs_harm": point, "direction": direction, "ci95": [float(x) for x in np.quantile(draws, [.025, .975])] if draws else None, "valid_bootstrap_draws": len(draws)}


STOP = {"the", "and", "was", "were", "has", "had", "with", "for", "from", "that", "this", "patient", "date", "note", "text", "time", "not"}


def terms(text):
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) >= 3 and token not in STOP}


def main():
    rows = list(csv.DictReader((P067 / "results.csv").open(encoding="utf-8-sig", newline="")))
    assert len(rows) == 236 and len({row["id"] for row in rows}) == 236
    cohort = [{"proposition_id": row["id"], "subject_id": row["sid"], "human_gt": row["GT"]} for row in rows]
    main_eval = {}
    for stage, base_key, candidate_key in (("raw", "baseline_raw", "new_raw"), ("priorg", "baseline_pg", "new_pg")):
        base, candidate = metric_rows(rows, base_key), metric_rows(rows, candidate_key)
        main_eval[stage] = {
            "baseline": evaluate(cohort, base, profile="research_patient", missing="error", iterations=1000),
            "candidate": evaluate(cohort, candidate, profile="research_patient", missing="error", iterations=1000),
            "paired": paired_compare(cohort, base, candidate, iterations=1000),
            "falseS_baseline": false_s(rows, base_key),
            "falseS_candidate": false_s(rows, candidate_key),
        }
    save(OUT / "unified_evaluation.json", main_eval)

    jobs = jsonl(OUT / "jobs_002.jsonl") + jsonl(OUT / "presentation_jobs.jsonl")
    answers = load_receipts(jobs)
    conditions = {(job["id"], job["condition"]): answers[job["request_id"]] for job in jobs}
    forensic = {x["id"]: x for x in jsonl(OUT / "forensic_cases.jsonl")}
    cases = {x["id"]: x for x in jsonl(P067 / "cases_blind.jsonl")}
    packs = {x["id"]: x for x in jsonl(P067 / "pack_mapping.jsonl")}
    feats = {x["id"]: x for x in jsonl(ROOT / "outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl")}
    by_id = {row["id"]: row for row in rows}
    selected = sorted({job["id"] for job in jobs if job["condition"] == "baseline_repeat"})
    assert len(selected) == 39
    detailed = []
    for pid in selected:
        prior = by_id[pid]
        rep_old = conditions[(pid, "baseline_repeat")]
        rep_new = conditions[(pid, "added_repeat")]
        linebreak = conditions.get((pid, "linebreak_presentation"), {"status": "identical_input_or_not_planned"})
        grp = forensic[pid]["group"]
        if rep_old["status"] == rep_new["status"] == "valid":
            repeat_group = "rescue" if rep_old["pg"] != prior["GT"] and rep_new["pg"] == prior["GT"] else "harm" if rep_old["pg"] == prior["GT"] and rep_new["pg"] != prior["GT"] else "unchanged"
            repeat_raw_group = "rescue" if rep_old["raw"] != prior["GT"] and rep_new["raw"] == prior["GT"] else "harm" if rep_old["raw"] == prior["GT"] and rep_new["raw"] != prior["GT"] else "unchanged"
        else:
            repeat_group = repeat_raw_group = "unavailable"
        scores = feats[pid]["ts_scores"]
        values = sorted((float(v) for v in scores.values()), reverse=True)
        claim_terms = terms(cases[pid]["claim"])
        selected_terms = set().union(*(terms(block) for block in re.split(r"(?:\n|\\n)\d+\. Date:", packs[pid]["final_reference"])))
        overlap = len(claim_terms & selected_terms) / len(claim_terms) if claim_terms else 0.0
        mp = packs[pid]
        f = forensic[pid]
        detailed.append({
            "id": pid, "sid": prior["sid"], "author": prior["author"], "GT": prior["GT"],
            "group": grp, "repeat_group": repeat_group, "repeat_raw_group": repeat_raw_group,
            "original_baseline_raw": prior["baseline_raw"], "original_short_raw": prior["new_raw"],
            "original_baseline_pg": prior["baseline_pg"], "original_short_pg": prior["new_pg"],
            "baseline_repeat": rep_old, "short_repeat": rep_new, "linebreak": linebreak,
            "baseline_self_flip_raw": rep_old.get("raw") != prior["baseline_raw"] if rep_old["status"] == "valid" else None,
            "short_self_flip_raw": rep_new.get("raw") != prior["new_raw"] if rep_new["status"] == "valid" else None,
            "baseline_self_flip_pg": rep_old.get("pg") != prior["baseline_pg"] if rep_old["status"] == "valid" else None,
            "short_self_flip_pg": rep_new.get("pg") != prior["new_pg"] if rep_new["status"] == "valid" else None,
            "novel_passages_n": f["added_passages_n"] - f["added_passages_full_text_in_original_n"],
            "original_retained_fraction": f["original_blocks_exactly_in_final_n"] / f["baseline_blocks_n"],
            "compression_fraction": 1 - f["final_blocks_n"] / f["baseline_blocks_n"],
            "baseline_score_margin": values[0] - values[1],
            "claim_selected_term_coverage": overlap,
            "unresolved_n": len(mp.get("unresolved", [])),
            "requirements_n": len(mp.get("requirements", [])),
            "direct_support_role": int("direct_support" in mp["addition_roles"]),
            "direct_contradiction_role": int("direct_contradiction" in mp["addition_roles"]),
        })

    with (OUT / "diagnostic_cases.jsonl").open("w", encoding="utf-8", newline="\n") as file:
        for entry in detailed:
            file.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
    flips = [entry for entry in detailed if entry["group"] in ("rescue", "harm")]
    stable = Counter((entry["group"], entry["repeat_group"]) for entry in flips)
    self_flips = {name: sum(entry[name] is True for entry in detailed) for name in ("baseline_self_flip_raw", "short_self_flip_raw", "baseline_self_flip_pg", "short_self_flip_pg")}
    linebreak_rows = [entry for entry in detailed if entry["linebreak"]["status"] == "valid"]
    linebreak = {
        "planned": sum(job["condition"] == "linebreak_presentation" for job in jobs),
        "valid": len(linebreak_rows),
        "vs_original_short_raw_different": sum(entry["linebreak"]["raw"] != entry["original_short_raw"] for entry in linebreak_rows),
        "vs_original_short_pg_different": sum(entry["linebreak"]["pg"] != entry["original_short_pg"] for entry in linebreak_rows),
        "vs_repeat_short_raw_different": sum(entry["short_repeat"]["status"] == "valid" and entry["linebreak"]["raw"] != entry["short_repeat"]["raw"] for entry in linebreak_rows),
        "vs_repeat_short_pg_different": sum(entry["short_repeat"]["status"] == "valid" and entry["linebreak"]["pg"] != entry["short_repeat"]["pg"] for entry in linebreak_rows),
        "different_from_both_when_short_self_stable_pg": sum(entry["short_repeat"]["status"] == "valid" and entry["original_short_pg"] == entry["short_repeat"]["pg"] and entry["linebreak"]["pg"] != entry["original_short_pg"] for entry in linebreak_rows),
    }
    feature_specs = [
        ("novel_passages_n", 1), ("original_retained_fraction", 1),
        ("compression_fraction", -1), ("baseline_score_margin", -1),
        ("claim_selected_term_coverage", 1), ("unresolved_n", -1),
        ("requirements_n", 1), ("direct_support_role", 1),
        ("direct_contradiction_role", 1),
    ]
    features = {}
    for name, direction in feature_specs:
        features[name] = {
            "rescue_mean": float(np.mean([entry[name] for entry in flips if entry["group"] == "rescue"])),
            "harm_mean": float(np.mean([entry[name] for entry in flips if entry["group"] == "harm"])),
            **patient_auc_ci(flips, name, direction),
        }
    stable_flips = [entry for entry in flips if entry["repeat_group"] == entry["group"]]
    stable_features = {}
    if {entry["group"] for entry in stable_flips} == {"rescue", "harm"}:
        for name, direction in feature_specs:
            stable_features[name] = patient_auc_ci(stable_flips, name, direction)
    repeat_jobs = [job for job in jobs if job["condition"] in ("baseline_repeat", "added_repeat")]
    all_cost = 0.0
    unknown_reserved = 0.0
    request_count = 0
    status_counts = Counter()
    import hashlib
    for job in jobs:
        folder = OUT / "attempts" / (hashlib.sha256(job["request_id"].encode()).hexdigest()[:24] + "_01")
        request = folder / "request.json"
        receipt = folder / "receipt.json"
        if not request.exists():
            continue
        request_count += 1
        if receipt.exists():
            tr = json.loads(receipt.read_text(encoding="utf-8"))["transport"]
            status_counts[str(tr.get("http_status"))] += 1
            all_cost += c.charge(job, tr)
        else:
            unknown_reserved += float(json.loads(request.read_text(encoding="utf-8"))["reservation_cny"])
    summary = {
        "main_cohort_n": len(rows), "main_patients": len({row["sid"] for row in rows}),
        "diagnostic_cases": len(detailed), "historical_flip_cases": len(flips),
        "repeat_statuses": {f"{a}/{b}": n for (a, b), n in Counter((entry["baseline_repeat"]["status"], entry["short_repeat"]["status"]) for entry in detailed).items()},
        "repeat_flip_matrix": {f"{a}->{b}": n for (a, b), n in stable.items()},
        "repeat_stable_flips": len(stable_flips),
        "repeat_stable_rescue_patients": len({entry["sid"] for entry in stable_flips if entry["group"] == "rescue"}),
        "repeat_stable_harm_patients": len({entry["sid"] for entry in stable_flips if entry["group"] == "harm"}),
        "self_flips": self_flips,
        "linebreak_presentation": linebreak,
        "signals_rescue_vs_harm": features,
        "signals_stable_rescue_vs_harm": stable_features,
        "cost": {"attempts": request_count, "http_status_counts": dict(status_counts), "estimated_usage_cny": all_cost, "unknown_reserved_cny": unknown_reserved, "occupied_cny": all_cost + unknown_reserved, "hard_cap_cny": 10.0},
        "reserved_used": False,
        "independent_audit": False,
    }
    save(OUT / "analysis.json", summary)
    print(json.dumps({k: summary[k] for k in ("diagnostic_cases", "repeat_statuses", "repeat_flip_matrix", "self_flips", "linebreak_presentation", "cost")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
