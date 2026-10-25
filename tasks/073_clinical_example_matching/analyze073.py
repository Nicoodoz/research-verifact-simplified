"""Unified paired raw/PriorG analysis for frozen 073 stages; offline only."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/073_clinical_example_matching"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(Path(__file__).parent))
from verifact_research.evaluation import evaluate, paired_compare  # noqa: E402
import common053 as c53  # noqa: E402
import run073  # noqa: E402

LABELS = c53.LABELS


def predlist(rows, mapping):
    return [{"proposition_id": x["id"], "verdict": mapping[x["id"]]} for x in rows]


def cohort(rows):
    return [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in rows]


def metric(rows, mapping):
    ev = evaluate(cohort(rows), predlist(rows, mapping), profile="research_patient", missing="error", iterations=1000)
    return {"n": len(rows), "correct": sum(mapping[x["id"]] == x["GT"] for x in rows),
            "PA": ev["percent_agreement"], "AC1": ev["gwet_ac1"], "MCC": ev["mcc"],
            "falseS": sum(x["GT"] != "Supported" and mapping[x["id"]] == "Supported" for x in rows),
            "recall": {k: ev["per_class"][k]["recall"] for k in LABELS},
            "confusion_matrix": ev["confusion_matrix"], "coverage": ev["coverage"]}


def compare(rows, before, after):
    pair = paired_compare(cohort(rows), predlist(rows, before), predlist(rows, after), iterations=1000)
    rescue = [x for x in rows if before[x["id"]] != x["GT"] and after[x["id"]] == x["GT"]]
    harm = [x for x in rows if before[x["id"]] == x["GT"] and after[x["id"]] != x["GT"]]
    patient = {}
    for sid in sorted({x["sid"] for x in rows}):
        subset = [x for x in rows if x["sid"] == sid]
        patient[sid] = sum(after[x["id"]] == x["GT"] for x in subset) - sum(before[x["id"]] == x["GT"] for x in subset)
    return {"n": len(rows), "rescue": len(rescue), "harm": len(harm), "net": len(rescue)-len(harm),
            "rescue_ids": [x["id"] for x in rescue], "harm_ids": [x["id"] for x in harm],
            "rescue_by_gt": dict(Counter(x["GT"] for x in rescue)),
            "harm_by_gt": dict(Counter(x["GT"] for x in harm)),
            "delta_falseS": sum(x["GT"] != "Supported" and after[x["id"]] == "Supported" for x in rows) -
                            sum(x["GT"] != "Supported" and before[x["id"]] == "Supported" for x in rows),
            "patient_net": patient, "paired": pair}


def write(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def write_lines(path, rows):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run(stage):
    run073.check_frozen(stage)
    frozen = run073.read(OUT / "freeze.json")
    ids = set(frozen["pilot_patients"] if stage in ("pilot", "adaptive") else frozen["confirmation_patients"])
    blind = {x["id"]: x for x in run073.lines(OUT / "target_blind.jsonl") if x["sid"] in ids}
    gold = {x["id"]: x for x in run073.lines(OUT / "target_gt.jsonl") if x["sid"] in ids}
    assert blind.keys() == gold.keys()
    rows = [{**blind[pid], **gold[pid]} for pid in blind]
    assert len(rows) == (36 if stage in ("pilot", "adaptive") else 60)
    fallback = run073.read(OUT / "fallback_u2.json")
    old_frozen = c53.read(ROOT / "outputs/053_thinking_prior_validation/freeze.json")
    attempts, answered = run073.attempt_state()
    jobs = run073.lines(OUT / f"{stage}_aliases.jsonl")
    assert len(jobs) == len({(j["id"], j["arm"]) for j in jobs}) and all(j["request_id"] in answered for j in jobs)
    arms = sorted({j["arm"] for j in jobs})
    maps, raw, invalid, details = {}, {}, {}, []
    for arm in arms:
        maps[arm], raw[arm], invalid[arm] = {}, {}, []
        for job in (j for j in jobs if j["arm"] == arm):
            pid = job["id"]
            parsed = answered[job["request_id"]]["parsed"]
            verdict = parsed.get("verdict") if parsed.get("status") in c53.VALID and parsed.get("verdict") in LABELS else None
            raw[arm][pid] = verdict
            valid_scores = parsed.get("status") in c53.VALID and parsed.get("scores") is not None
            if valid_scores:
                logits = c53.calibrated(parsed["scores"], old_frozen["calibration_theta"]["T-S"]["G"], "G")
                logits = c53.prior_adjust(logits, old_frozen["reference_prior_counts"], old_frozen["calibration_counts"]["T-S"])
                maps[arm][pid] = c53.decode_logits(logits)
            else:
                maps[arm][pid] = fallback[pid]
                invalid[arm].append(pid)
            usage = parsed.get("usage") or {}
            details.append({"stage": stage, "id": pid, "sid": job["sid"], "arm": arm,
                            "request_id": job["request_id"], "attempt_id": answered[job["request_id"]]["attempt_id"],
                            "GT": gold[pid]["GT"], "raw": verdict, "PriorG": maps[arm][pid],
                            "scores": parsed.get("scores"), "parsed_status": parsed.get("status"),
                            "fallback": not valid_scores, "reasoning_present": parsed.get("reasoning_present"),
                            "usage": usage})
        assert len(maps[arm]) == len(rows)
    common_raw = [x for x in rows if all(raw[arm][x["id"]] in LABELS for arm in arms)]
    metrics = {arm: metric(rows, maps[arm]) for arm in arms}
    raw_metrics = {arm: metric(common_raw, raw[arm]) for arm in arms} if common_raw else None
    final_pairs, raw_pairs = {}, {}
    for arm in arms:
        if arm != "B" and "B" in arms:
            final_pairs[arm + "_minus_B"] = compare(rows, maps["B"], maps[arm])
            if common_raw:
                raw_pairs[arm + "_minus_B"] = compare(common_raw, raw["B"], raw[arm])
        if arm not in ("B", "F4") and "F4" in arms:
            final_pairs[arm + "_minus_F4"] = compare(rows, maps["F4"], maps[arm])
            if common_raw:
                raw_pairs[arm + "_minus_F4"] = compare(common_raw, raw["F4"], raw[arm])
    cost_by_arm = defaultdict(float)
    attempt_count_by_arm = Counter()
    for attempt in attempts:
        if attempt["stage"] == stage:
            cost_by_arm[attempt["arm"]] += attempt["cost_cny"]
            attempt_count_by_arm[attempt["arm"]] += 1
    tokens = {}
    for arm in arms:
        group = [d for d in details if d["arm"] == arm]
        tokens[arm] = {"prompt_total": sum(int(d["usage"].get("prompt_tokens", 0)) for d in group),
                       "completion_total": sum(int(d["usage"].get("completion_tokens", 0)) for d in group),
                       "prompt_mean": sum(int(d["usage"].get("prompt_tokens", 0)) for d in group) / len(group),
                       "completion_mean": sum(int(d["usage"].get("completion_tokens", 0)) for d in group) / len(group)}
    result = {"stage": stage, "n": len(rows), "patients": len(ids), "GT_counts": dict(Counter(x["GT"] for x in rows)),
              "arms": arms, "raw_common_n": len(common_raw), "raw_missing_ids": sorted(set(blind)-{x["id"] for x in common_raw}),
              "invalid_by_arm": invalid, "final_metrics": metrics, "raw_metrics": raw_metrics,
              "final_pairs": final_pairs, "raw_pairs": raw_pairs,
              "cost_by_arm_cny": dict(cost_by_arm), "cost_attribution_note": "shared bodies physically charged once to canonical job arm",
              "author_metrics": {author: {arm: metric([x for x in rows if x["author"] == author], maps[arm]) for arm in arms} for author in sorted({x["author"] for x in rows})}, "attempt_count_by_arm": dict(attempt_count_by_arm),
              "tokens_by_arm": tokens, "task_total_used_or_reserved_cny": sum(x["cost_cny"] for x in attempts)}
    write(OUT / f"{stage}_analysis.json", result)
    write_lines(OUT / f"{stage}_predictions.jsonl", details)
    print(json.dumps({"stage": stage, "n": len(rows), "GT": result["GT_counts"],
                      "raw_common_n": len(common_raw),
                      "metrics": {a: {k: metrics[a][k] for k in ("correct", "MCC", "falseS")} for a in arms},
                      "pairs": {k: {f: p[f] for f in ("rescue", "harm", "net", "delta_falseS")} for k, p in final_pairs.items()},
                      "task_cost_cny": result["task_total_used_or_reserved_cny"]}, ensure_ascii=False))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("pilot", "adaptive", "confirmation"))
    run(p.parse_args().stage)
