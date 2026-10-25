"""Frozen 071 paired analysis, gate and optional exact-body repeat analysis."""
from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/071_judge_icl_feasibility"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(ROOT / "tasks/071_judge_icl_feasibility"))
from verifact_research.evaluation import evaluate, paired_compare  # noqa: E402
import common053 as c53  # noqa: E402
import run071  # noqa: E402

LABELS = c53.LABELS


def jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8-sig").splitlines() if s.strip()]


def write(path, obj):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def preds(rows, mapping):
    return [{"proposition_id": x["id"], "verdict": mapping[x["id"]]} for x in rows]


def cohort(rows):
    return [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in rows]


def metric(rows, mapping):
    ev = evaluate(cohort(rows), preds(rows, mapping), profile="research_patient", missing="error", iterations=1000)
    return {"n": len(rows), "correct": sum(mapping[x["id"]] == x["GT"] for x in rows),
            "PA": ev["percent_agreement"], "AC1": ev["gwet_ac1"], "MCC": ev["mcc"],
            "falseS": sum(x["GT"] != "Supported" and mapping[x["id"]] == "Supported" for x in rows),
            "recall": {k: ev["per_class"][k]["recall"] for k in LABELS},
            "confusion_matrix": ev["confusion_matrix"], "coverage": ev["coverage"]}


def compare(rows, before, after):
    pair = paired_compare(cohort(rows), preds(rows, before), preds(rows, after), iterations=1000)
    rescue = [x for x in rows if before[x["id"]] != x["GT"] and after[x["id"]] == x["GT"]]
    harm = [x for x in rows if before[x["id"]] == x["GT"] and after[x["id"]] != x["GT"]]
    return {"n": len(rows), "rescue": len(rescue), "harm": len(harm), "net": len(rescue)-len(harm),
            "rescue_ids": [x["id"] for x in rescue], "harm_ids": [x["id"] for x in harm],
            "rescue_patients": len({x["sid"] for x in rescue}), "harm_patients": len({x["sid"] for x in harm}),
            "rescue_by_gt": dict(Counter(x["GT"] for x in rescue)), "harm_by_gt": dict(Counter(x["GT"] for x in harm)),
            "rescue_by_author": dict(Counter(x["author"] for x in rescue)), "harm_by_author": dict(Counter(x["author"] for x in harm)),
            "delta_falseS": sum(x["GT"] != "Supported" and after[x["id"]] == "Supported" for x in rows) -
                            sum(x["GT"] != "Supported" and before[x["id"]] == "Supported" for x in rows),
            "paired": pair}


def mapped(jobs, terminal, ids, fallback):
    pg = {}
    raw = {}
    invalid = []
    details = []
    frozen = c53.read(ROOT / "outputs/053_thinking_prior_validation/freeze.json")
    for job in jobs:
        rid, pid = job["request_id"], job["id"]
        if pid not in ids:
            continue
        rec = terminal[rid]
        parsed = rec["parsed"]
        is_valid = parsed.get("status") in c53.VALID and parsed.get("scores") is not None
        verdict = parsed.get("verdict") if parsed.get("status") in c53.VALID and parsed.get("verdict") in LABELS else None
        raw[pid] = verdict
        if is_valid:
            z = c53.calibrated(parsed["scores"], frozen["calibration_theta"]["T-S"]["G"], "G")
            z = c53.prior_adjust(z, frozen["reference_prior_counts"], frozen["calibration_counts"]["T-S"])
            pg[pid] = c53.decode_logits(z)
        else:
            pg[pid] = fallback[pid]
            invalid.append(pid)
        details.append({"id": pid, "request_id": rid, "arm": job["arm"], "parsed_status": parsed.get("status"),
                        "raw": verdict, "PriorG": pg[pid], "scores": parsed.get("scores"),
                        "fallback": not is_valid, "reasoning_present": parsed.get("reasoning_present"),
                        "usage": parsed.get("usage"), "recovered_by_request_id": rec.get("recovered_by_request_id")})
    return pg, raw, invalid, details


def run(stage):
    run071.check_frozen()
    eval_blind = {x["id"]: x for x in jsonl(OUT / "evaluation_blind.jsonl")}
    eval_gt = {x["id"]: x for x in jsonl(OUT / "evaluation_gt.jsonl")}
    assert set(eval_blind) == set(eval_gt) and len(eval_gt) == 96
    rows = [{**eval_blind[pid], **eval_gt[pid]} for pid in eval_blind]
    fallback = {r["id"]: r["U2"] for r in csv.DictReader((ROOT / "outputs/053_thinking_prior_validation/predictions.csv").open(encoding="utf-8-sig", newline="")) if r["id"] in eval_gt}
    historical = {r["id"]: r["TS_PriorG"] for r in csv.DictReader((ROOT / "outputs/053_thinking_prior_validation/predictions.csv").open(encoding="utf-8-sig", newline="")) if r["id"] in eval_gt}
    assert len(fallback) == len(historical) == 96
    attempts, terminal = run071.resolved_state()
    if stage == "stage1":
        jobs = jsonl(OUT / "main_jobs.jsonl")
        assert len(jobs) == 288 and all(j["request_id"] in terminal for j in jobs)
        arms = {arm: [j for j in jobs if j["arm"] == arm] for arm in ("B", "E", "C")}
        maps, raws, invalid, details = {}, {}, {}, []
        for arm, js in arms.items():
            maps[arm], raws[arm], invalid[arm], d = mapped(js, terminal, eval_gt, fallback)
            details.extend(d)
        assert all(len(maps[a]) == 96 for a in arms)
        common_raw = [x for x in rows if all(raws[a][x["id"]] in LABELS for a in arms)]
        final_metrics = {a: metric(rows, maps[a]) for a in arms}
        raw_metrics = {a: metric(common_raw, raws[a]) for a in arms} if common_raw else None
        final_pairs = {"E_minus_B": compare(rows, maps["B"], maps["E"]),
                       "E_minus_C": compare(rows, maps["C"], maps["E"]),
                       "C_minus_B": compare(rows, maps["B"], maps["C"])}
        raw_pairs = {"E_minus_B": compare(common_raw, raws["B"], raws["E"]),
                     "E_minus_C": compare(common_raw, raws["C"], raws["E"])} if common_raw else None
        result = {"stage": stage, "n": 96, "patients": 16, "GT": dict(Counter(x["GT"] for x in rows)),
                  "raw_common_n": len(common_raw), "raw_missing_ids": sorted(set(eval_gt)-{x["id"] for x in common_raw}),
                  "invalid_by_arm": invalid, "final_metrics": final_metrics, "raw_metrics": raw_metrics,
                  "final_pairs": final_pairs, "raw_pairs": raw_pairs,
                  "historical_pg": metric(rows, historical), "B_vs_historical": compare(rows, historical, maps["B"]),
                  "cost_used_reserved_cny": run071.PRIOR_RESERVED + sum(x["cost_cny"] for x in attempts),
                  "paid_attempts_071": len(attempts)}
        write(OUT / "stage1_analysis.json", result)
        with (OUT / "stage1_predictions.jsonl").open("x", encoding="utf-8", newline="\n") as f:
            for row in details:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        a, b = final_pairs["E_minus_B"], final_pairs["E_minus_C"]
        positive = a["net"] >= 5 and a["delta_falseS"] <= 1 and a["paired"]["metrics"]["mcc"]["delta"] >= 0 and b["net"] >= 3
        arm_cost = defaultdict(float)
        rid_arm = {j["request_id"]: j["arm"] for j in jobs}
        recovery_file = OUT / "recovery_jobs.jsonl"
        if recovery_file.exists():
            rid_arm.update({j["request_id"]: j["arm"] for j in jsonl(recovery_file)})
        for attempt in attempts:
            if attempt["id"] in rid_arm:
                arm_cost[rid_arm[attempt["id"]]] += attempt["cost_cny"]
        projected_repeat = arm_cost["B"] + arm_cost["E"]
        # 20% cushion for repeat usage variability plus six largest in-flight reservations.
        enough_budget = result["cost_used_reserved_cny"] + projected_repeat * 1.2 + 0.8 <= 20
        gate = {"frozen_gate_conditions": {"E_minus_B_net_ge5": a["net"] >= 5,
                    "E_minus_B_falseS_delta_le1": a["delta_falseS"] <= 1,
                    "E_minus_B_MCC_nondecrease": a["paired"]["metrics"]["mcc"]["delta"] >= 0,
                    "E_minus_C_net_ge3": b["net"] >= 3},
                "effect_gate": positive, "budget_gate": enough_budget,
                "projected_repeat_cny": projected_repeat,
                "stage2_authorized_by_frozen_gate": bool(positive and enough_budget),
                "no_positive_claim_without_full_repeat": True}
        write(OUT / "stage1_gate.json", gate)
        if gate["stage2_authorized_by_frozen_gate"]:
            repeat = []
            for j in jobs:
                if j["arm"] not in ("B", "E"):
                    continue
                z = dict(j)
                z["request_id"] = j["request_id"].replace("071_", "071_repeat_", 1)
                z["stage"] = "repeat"
                z["source_request_id"] = j["request_id"]
                repeat.append(z)
            repeat.sort(key=lambda j: hashlib.sha256(("071/repeat/v1:"+j["id"]+j["arm"]).encode()).hexdigest())
            with (OUT / "repeat_jobs.jsonl").open("x", encoding="utf-8", newline="\n") as f:
                for j in repeat:
                    f.write(json.dumps(j, ensure_ascii=False, sort_keys=True) + "\n")
        print(json.dumps({"n": 96, "metrics": {a: {k: final_metrics[a][k] for k in ("correct", "MCC", "falseS")} for a in arms},
                          "E_B": {k: a[k] for k in ("rescue", "harm", "net", "delta_falseS")},
                          "E_C": {k: b[k] for k in ("rescue", "harm", "net")},
                          "gate": gate, "cost": result["cost_used_reserved_cny"]}, ensure_ascii=False))
    elif stage == "repeat":
        jobs = jsonl(OUT / "repeat_jobs.jsonl")
        assert len(jobs) == 192 and all(j["request_id"] in terminal for j in jobs)
        maps, raws, invalid = {}, {}, {}
        for arm in ("B", "E"):
            maps[arm], raws[arm], invalid[arm], _ = mapped([j for j in jobs if j["arm"] == arm], terminal, eval_gt, fallback)
        first = jsonl(OUT / "stage1_predictions.jsonl")
        firstmaps = {a: {x["id"]: x["PriorG"] for x in first if x["arm"] == a} for a in ("B", "E")}
        pair = compare(rows, maps["B"], maps["E"])
        first_rescue = set(run071.read(OUT / "stage1_analysis.json")["final_pairs"]["E_minus_B"]["rescue_ids"])
        kept = sorted(pid for pid in first_rescue if maps["E"][pid] == eval_gt[pid]["GT"] and maps["B"][pid] != eval_gt[pid]["GT"])
        result = {"stage": stage, "n": 96, "metrics": {a: metric(rows, maps[a]) for a in ("B", "E")},
                  "E_minus_B": pair, "invalid_by_arm": invalid,
                  "agreement_with_first": {a: sum(firstmaps[a][pid] == maps[a][pid] for pid in eval_gt) for a in ("B", "E")},
                  "first_rescue_n": len(first_rescue), "first_rescue_kept_n": len(kept), "first_rescue_kept_ids": kept,
                  "cost_used_reserved_cny": run071.PRIOR_RESERVED + sum(x["cost_cny"] for x in attempts)}
        write(OUT / "repeat_analysis.json", result)
        print(json.dumps({"metrics": {a: {k: result["metrics"][a][k] for k in ("correct", "MCC", "falseS")} for a in ("B", "E")},
                          "E_B": {k: pair[k] for k in ("rescue", "harm", "net", "delta_falseS")},
                          "first_rescue_kept": [len(kept), len(first_rescue)],
                          "cost": result["cost_used_reserved_cny"]}, ensure_ascii=False))
    else:
        raise ValueError(stage)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("stage1", "repeat"))
    run(p.parse_args().stage)
