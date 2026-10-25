"""081 preregistered full-cohort analysis using the common evaluation implementation."""
from __future__ import annotations

import csv
import datetime
import json
import math
import statistics
import sys
from collections import Counter, defaultdict

import blind081 as b
import run081 as r

sys.path.insert(0, str(b.ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(b.ROOT / "tasks/066_oracle_headroom"))
from common053 import LABELS, VALID, parse_response, decision
from common066 import priorg
from verifact_research.evaluation import evaluate, paired_compare


def write(name, value):
    with (b.OUT / name).open("x", encoding="utf-8", newline="\n") as f:
        if isinstance(value, list):
            for x in value:
                f.write(json.dumps(x, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
        else:
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.write("\n")


def old_u2():
    prior = {x["id"]: x for x in b.lines("outputs/078_component_ablation/predictions.jsonl")}
    newer = {x["proposition_id"]: x for x in b.lines("outputs/031_training_expansion_confirmation/inference_001/confirmation_predictions_blind.jsonl")}
    out = {}
    for x in b.lines("outputs/081_gt_blind_evidence_selection/sample_blind.jsonl"):
        if x["stage"] != 1:
            continue
        pid = x["id"]
        if pid in prior:
            out[pid] = prior[pid]["methods"]["NS_U2"]["label"]
        else:
            out[pid] = LABELS[int(newer[pid]["u2"])]
        assert out[pid] in LABELS
    return out, prior


def released_original():
    rows = {}
    for author in ("human", "llm"):
        path = f"outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv"
        with (b.ROOT / path).open(encoding="utf-8-sig", newline="") as f:
            for x in csv.DictReader(f):
                rows[x["proposition_id"]] = x["verdict"]
    return rows


def cohort(rows):
    return [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in rows]


def preds(rows, arm, mode):
    return [{"proposition_id": x["id"], "verdict": x["methods"][arm][mode]} for x in rows]


def score(rows, arm, mode, ci=True):
    ev = evaluate(cohort(rows), preds(rows, arm, mode),
                  profile="research_patient" if ci else "none", iterations=1000, missing="error")
    false_s = sum(x["methods"][arm][mode] == "Supported" and x["GT"] != "Supported" for x in rows)
    non_s = sum(x["GT"] != "Supported" for x in rows)
    return {"arm": arm, "mode": mode, "n": len(rows), "patients": len({x["sid"] for x in rows}),
            "correct": sum(x["methods"][arm][mode] == x["GT"] for x in rows),
            "PA": ev["percent_agreement"], "MCC": ev["mcc"], "AC1": ev["gwet_ac1"],
            "false_S": false_s, "false_S_rate_nonS": false_s / non_s,
            "nonS_denominator": non_s, "per_class": ev["per_class"],
            "confusion_matrix": ev["confusion_matrix"], "CI95": ev.get("confidence_intervals"),
            "coverage": ev["coverage"]}


def pair(rows, base, cand, mode):
    pc = paired_compare(cohort(rows), preds(rows, base, mode), preds(rows, cand, mode), iterations=1000)
    rescue = [x for x in rows if x["methods"][base][mode] != x["GT"] and x["methods"][cand][mode] == x["GT"]]
    harm = [x for x in rows if x["methods"][base][mode] == x["GT"] and x["methods"][cand][mode] != x["GT"]]
    pn = {sid: sum((x in rescue) - (x in harm) for x in rows if x["sid"] == sid)
          for sid in sorted({x["sid"] for x in rows})}
    return {"base": base, "candidate": cand, "mode": mode, "n": len(rows),
            "rescue": len(rescue), "harm": len(harm), "net": len(rescue) - len(harm),
            "rescue_ids": [x["id"] for x in rescue], "harm_ids": [x["id"] for x in harm],
            "patient_wins": sum(v > 0 for v in pn.values()),
            "patient_losses": sum(v < 0 for v in pn.values()),
            "patient_ties": sum(v == 0 for v in pn.values()), "patient_net": pn,
            "rescue_patients": len({x["sid"] for x in rescue}),
            "delta_false_S": sum((x["methods"][cand][mode] == "Supported")
                                 - (x["methods"][base][mode] == "Supported")
                                 for x in rows if x["GT"] != "Supported"),
            "metrics": pc["metrics"],
            "gt_rescue": dict(Counter(x["GT"] for x in rescue)),
            "gt_harm": dict(Counter(x["GT"] for x in harm))}


def pack_stats(x, ups, tps):
    bid = x["baseline_ids"]
    pack_ids = {"B": bid, "U": ups[x["id"]]["pack"]["selected_ids"],
                "T": tps[x["id"]]["pack"]["selected_ids"]}
    refs = {"B": x["baseline_reference"], "U": ups[x["id"]]["pack"]["reference"],
            "T": tps[x["id"]]["pack"]["reference"]}
    result = {}
    for arm in ("B", "U", "T"):
        ids = pack_ids[arm]
        result[arm] = {"passage_ids": ids, "n": len(ids), "reference_chars": len(refs[arm]),
                       "reference_sha256": __import__("hashlib").sha256(refs[arm].encode()).hexdigest(),
                       "added_vs_B": len(set(ids) - set(bid)), "deleted_vs_B": len(set(bid) - set(ids)),
                       "intersection_vs_B": len(set(ids) & set(bid)),
                       "jaccard_vs_B": len(set(ids) & set(bid)) / len(set(ids) | set(bid))}
    result["UT_jaccard"] = len(set(pack_ids["U"]) & set(pack_ids["T"])) / len(set(pack_ids["U"]) | set(pack_ids["T"]))
    result["UT_same_reference"] = refs["U"] == refs["T"]
    return result


def main():
    freeze = r.read(b.OUT / "judge_extra_freeze.json")
    assert freeze["jobs_sha256"] == b.sha(b.OUT / "judge_jobs.jsonl")
    jobs = r.jobs("judge")
    attempts, success = r.state()
    assert all(j["request_id"] in success for j in jobs), "No partial primary analysis"
    assert len(jobs) == 288
    total = sum(x["cost_cny"] for x in attempts)
    assert total <= 20
    labels = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/stage1_labels.jsonl")}
    ups = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/u_packs.jsonl")}
    tps = {x["id"]: x for x in b.lines("outputs/081_gt_blind_evidence_selection/t_packs.jsonl")}
    fallback, old = old_u2()
    originals = released_original()
    by_id_arm = {(j["id"], j["arm"]): j for j in jobs}
    records, invalid = [], []
    for x in b.lines("outputs/081_gt_blind_evidence_selection/sample_blind.jsonl"):
        if x["stage"] != 1:
            continue
        pid = x["id"]
        rec = {"id": pid, "sid": x["sid"], "author": x["author"], "GT": labels[pid]["GT"],
               "previously_exposed": x["previously_exposed"], "source": x["source"],
               "methods": {}, "arms": {}, "pack_stats": pack_stats(x, ups, tps),
               "original_verifact": originals[pid]}
        for arm in ("B", "U", "T"):
            job = by_id_arm[pid, arm]
            answer = success[job["request_id"]]
            parsed = parse_response(answer["transport"], True, True)
            valid = parsed["status"] in VALID and parsed.get("scores") is not None
            if valid:
                scores = parsed["scores"]
                method = {"raw": parsed["verdict"], "U0": decision(scores, 0), "PriorG": priorg(scores)}
            else:
                method = {"raw": fallback[pid], "U0": fallback[pid], "PriorG": fallback[pid]}
                invalid.append({"id": pid, "arm": arm, "status": parsed["status"],
                                "errors": parsed.get("errors"), "fallback": fallback[pid]})
            rec["arms"][arm] = {"status": parsed["status"], "valid": valid,
                                "raw_verdict": parsed.get("verdict"), "scores": parsed.get("scores"),
                                "usage": parsed.get("usage"), "reason": parsed.get("reason"),
                                "body_sha256": job["body_sha256"],
                                "attempt_id": answer["attempt"]["attempt_id"],
                                "receipt_path": answer["attempt"]["path"].replace("request.json", "receipt.json"),
                                "cost_cny": answer["attempt"]["cost_cny"],
                                "started_utc": answer["transport"].get("started_utc"),
                                "ended_utc": answer["transport"].get("ended_utc")}
            rec["methods"][arm] = method
        prior = old.get(pid)
        if prior and prior["arms"]["TS"]["body_sha256"] == rec["arms"]["B"]["body_sha256"]:
            p = prior["arms"]["TS"]
            if p["valid"] and p["scores"] is not None:
                assert priorg(p["scores"]) == prior["methods"]["TS_PriorG"]["label"]
                rec["old_B"] = {"raw": p["raw"], "U0": decision(p["scores"], 0),
                                "PriorG": priorg(p["scores"]), "scores": p["scores"],
                                "body_sha256": p["body_sha256"], "receipt_source": p["receipt_source"]}
        records.append(rec)
    assert len(records) == 96 and len({x["id"] for x in records}) == 96
    full = [score(records, arm, mode) for mode in ("raw", "U0", "PriorG") for arm in ("B", "U", "T")]
    pairs = [pair(records, a, z, mode) for mode in ("raw", "U0", "PriorG")
             for a, z in (("B", "U"), ("B", "T"), ("U", "T"))]
    core = [x for x in records if all(x["arms"][arm]["valid"] for arm in ("B", "U", "T"))]
    core_metrics = [score(core, arm, mode, False) for mode in ("raw", "U0", "PriorG")
                    for arm in ("B", "U", "T")] if core else []
    old_rows = [x for x in records if "old_B" in x]
    fluctuations = {mode: {"n": len(old_rows),
                           "flips": sum(x["old_B"][mode] != x["methods"]["B"][mode] for x in old_rows),
                           "old_correct": sum(x["old_B"][mode] == x["GT"] for x in old_rows),
                           "new_correct": sum(x["methods"]["B"][mode] == x["GT"] for x in old_rows)}
                    for mode in ("raw", "U0", "PriorG")}
    tp = next(x for x in pairs if x["base"] == "B" and x["candidate"] == "T" and x["mode"] == "PriorG")
    up = next(x for x in pairs if x["base"] == "B" and x["candidate"] == "U" and x["mode"] == "PriorG")
    reliable_t = [x["id"] for x in records if "old_B" in x and x["old_B"]["PriorG"] != x["GT"]
                  and x["methods"]["B"]["PriorG"] != x["GT"] and x["methods"]["T"]["PriorG"] == x["GT"]]
    teacher_gate = (tp["net"] >= 3 and tp["rescue_patients"] >= 3 and tp["patient_wins"] > tp["patient_losses"]
                    and tp["delta_false_S"] <= 2 and max(tp["patient_net"].values()) < tp["net"]
                    and len(reliable_t) >= 2)
    blind_gate = (up["net"] >= 2 and up["rescue_patients"] >= 2
                  and up["patient_wins"] >= up["patient_losses"] and up["delta_false_S"] <= 2
                  and any(q["net"] >= 0 and q["metrics"]["mcc"]["delta"] >= 0
                          for q in pairs if q["base"] == "B" and q["candidate"] == "U"
                          and q["mode"] in ("raw", "PriorG")))
    event = []
    for x in records:
        b_good = x["methods"]["B"]["PriorG"] == x["GT"]
        t_good = x["methods"]["T"]["PriorG"] == x["GT"]
        change = "beneficial" if t_good and not b_good else "harmful" if b_good and not t_good else "no_change"
        if "old_B" in x and x["old_B"]["PriorG"] != x["methods"]["B"]["PriorG"]:
            change = "unstable_baseline" if change != "no_change" else change
        event.append({"id": x["id"], "sid": x["sid"], "GT": x["GT"], "class": change,
                      "T_added": x["pack_stats"]["T"]["added_vs_B"],
                      "T_deleted": x["pack_stats"]["T"]["deleted_vs_B"],
                      "T_jaccard": x["pack_stats"]["T"]["jaccard_vs_B"]})
    stable_ben = [x for x in event if x["class"] == "beneficial"]
    stable_harm = [x for x in event if x["class"] == "harmful"]
    learnability = (teacher_gate and not blind_gate and len(stable_ben) + len(stable_harm) >= 8
                    and len({x["sid"] for x in stable_ben}) >= 4
                    and len({x["GT"] for x in stable_ben}) >= 2)
    original_ev = evaluate(cohort(records),
                           [{"proposition_id": x["id"], "verdict": x["original_verifact"]} for x in records],
                           profile="research_patient", missing="error", iterations=1000)
    original_row = {"config": "作者原VeriFact R1-70B，同96 ID历史发布预测", "n": 96,
                    "correct": sum(x["original_verifact"] == x["GT"] for x in records),
                    "PA": original_ev["percent_agreement"], "MCC": original_ev["mcc"],
                    "AC1": original_ev["gwet_ac1"],
                    "false_S": sum(x["original_verifact"] == "Supported" and x["GT"] != "Supported" for x in records),
                    "per_class": original_ev["per_class"], "confusion_matrix": original_ev["confusion_matrix"]}
    by_author = {}
    for author in ("human", "llm"):
        subset = [x for x in records if x["author"] == author]
        by_author[author] = {"n": len(subset), "GT": dict(Counter(x["GT"] for x in subset)),
                             "PriorG": {arm: {"correct": sum(x["methods"][arm]["PriorG"] == x["GT"] for x in subset),
                                               "false_S": sum(x["methods"][arm]["PriorG"] == "Supported" and x["GT"] != "Supported" for x in subset)}
                                        for arm in ("B", "U", "T")}}
    pack_summary = {arm: {"passages_mean": statistics.mean(x["pack_stats"][arm]["n"] for x in records),
                          "reference_chars_mean": statistics.mean(x["pack_stats"][arm]["reference_chars"] for x in records),
                          "added_vs_B_mean": statistics.mean(x["pack_stats"][arm]["added_vs_B"] for x in records),
                          "deleted_vs_B_mean": statistics.mean(x["pack_stats"][arm]["deleted_vs_B"] for x in records),
                          "same_reference_as_B": sum(x["pack_stats"][arm]["reference_sha256"] == x["pack_stats"]["B"]["reference_sha256"] for x in records)}
                    for arm in ("B", "U", "T")}
    for arm in ("B", "U", "T"):
        pack_summary[arm]["judge_prompt_tokens_mean"] = statistics.mean(x["arms"][arm]["usage"]["prompt_tokens"] for x in records)
        pack_summary[arm]["judge_completion_tokens_mean"] = statistics.mean(x["arms"][arm]["usage"]["completion_tokens"] for x in records)
        pack_summary[arm]["judge_cost_cny_mean"] = statistics.mean(x["arms"][arm]["cost_cny"] for x in records)
        pack_summary[arm]["judge_latency_seconds_mean"] = statistics.mean(
            (datetime.datetime.fromisoformat(x["arms"][arm]["ended_utc"])
             - datetime.datetime.fromisoformat(x["arms"][arm]["started_utc"])).total_seconds() for x in records)
    pack_summary["UT_overlap_jaccard_mean"] = statistics.mean(x["pack_stats"]["UT_jaccard"] for x in records)
    overlap_paths = ["outputs/066_oracle_headroom/error_cases.jsonl",
                     "outputs/067_conservative_evidence_packing/cases_blind.jsonl",
                     "outputs/067_conservative_evidence_packing/cases_blind_v2.jsonl",
                     "outputs/068_final_pack_utility_diagnosis/diagnostic_cases.jsonl",
                     "outputs/068_final_pack_utility_diagnosis/diagnostic_v2_cases.jsonl",
                     "outputs/069_final_pack_controlled_repair/stage1_final_cases.jsonl"]
    historical_overlap = {}
    for path in overlap_paths:
        if (b.ROOT / path).exists():
            ids = {str(z.get("id") or z.get("proposition_id")) for z in b.lines(path)}
            historical_overlap[path] = sorted(x["id"] for x in records if x["id"] in ids)
    summary = {"n": 96, "patients": 24, "GT": dict(Counter(x["GT"] for x in records)),
               "author": dict(Counter(x["author"] for x in records)),
               "new_claim_n": sum(not x["previously_exposed"] for x in records),
               "cost_cny": total, "attempts": len(attempts), "logical_requests": len(success),
               "invalid": invalid, "core_common_n": len(core),
               "metrics": full, "pairs": pairs, "core_metrics": core_metrics,
               "original_verifact": original_row, "by_author": by_author,
               "pack_summary": pack_summary, "historical_066_069_overlap": historical_overlap,
               "old_B_fluctuation": fluctuations, "old_B_matched_n": len(old_rows),
               "oldB_newB_wrong_T_right_ids": reliable_t,
               "teacher_gate": teacher_gate, "blind_gate": blind_gate,
               "learnability_gate": learnability,
               "intervention_classes": dict(Counter(x["class"] for x in event)),
               "stage2_cost_feasible": 20 - total >= r.read(b.OUT / "stage1_cost_estimate.json")["projected_base_cny"]}
    write("case_results.jsonl", records)
    write("teacher_intervention_events.jsonl", event)
    write("results.json", summary)
    write("cost_ledger.json", {"cap_cny": 20, "estimated_cost_cny": total,
                               "attempts": attempts, "stage_costs": dict(Counter({stage: sum(x["cost_cny"] for x in attempts if x["stage"] == stage) for stage in r.STAGES})),
                               "unknown_attempts": [x for x in attempts if x["http_status"] == 0]})
    print(json.dumps({"n": 96, "cost": total, "teacher_gate": teacher_gate,
                      "blind_gate": blind_gate, "fallback": len(invalid),
                      "priorg": [(x["arm"], x["correct"], x["MCC"], x["false_S"]) for x in full if x["mode"] == "PriorG"],
                      "old_B_matched_n": len(old_rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
