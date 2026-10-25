"""Apply frozen rules and the shared evaluator to 084 and untouched 082 cases."""
import csv
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/084_f4_coverage_validation"))
sys.path.insert(0, str(ROOT / "tasks/053_thinking_prior_validation"))
sys.path.insert(0, str(ROOT / "tasks/066_oracle_headroom"))
from verifact_research.evaluation import evaluate, paired_compare
from common053 import VALID, parse_response, decision
from common066 import priorg
import run084

LABELS = ("Supported", "Not Supported", "Not Addressed")


def lines(path):
    return [json.loads(s) for s in Path(path).open(encoding="utf-8-sig") if s.strip()]


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_lines(path, objects):
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        for obj in objects:
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


def master(ids):
    gt, original = {}, {}
    source = ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    with source.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            pid = row["proposition_id"]
            if pid in ids:
                assert row["proposition_type"] == "claim" and row["invalid"] == "False"
                assert row["human_gt"] in LABELS
                gt[pid] = row
    assert set(gt) == ids
    for author in ("human", "llm"):
        path = ROOT / f"outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv"
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row["proposition_id"] in ids:
                    original[row["proposition_id"]] = row["verdict"]
    assert set(original) == ids and all(x in LABELS for x in original.values())
    return gt, original, hashlib.sha256(source.read_bytes()).hexdigest()


def new_records():
    sample = lines(OUT / "sample_blind.jsonl")
    teaching_patients = set(run084.read(ROOT / "outputs/071_judge_icl_feasibility/freeze.json")["training_patients"])
    jobs = lines(OUT / "main_jobs.jsonl")
    jobmap = {(x["id"], x["arm"]): x for x in jobs}
    attempts, success, counts = run084.state()
    assert len(success) == 360, f"new main pairs incomplete: {len(success)}/360"
    ids = {x["id"] for x in sample}
    gt, original, gtsha = master(ids)
    rows = []
    invalid = []
    native_manifest = []
    for x in sample:
        pid, sid = x["id"], x["sid"]
        doc = gt[pid]
        assert doc["subject_id"] == sid and doc["author_type"] == x["author"]
        row = {"id": pid, "sid": sid, "author": x["author"], "GT": doc["human_gt"],
               "cohort": "new084", "original_verifact": original[pid],
               "fallback_label": x["fallback_U2"], "reference_sha256": x["reference_sha256"],
               "material_sources": x["material_sources"], "teaching_exposure": x["teaching_exposure"],
               "full_candidate_pool_overlap": x["full_candidate_pool_overlap"],
               "teaching_candidate_patient_overlap": sid in teaching_patients, "arms": {}, "methods": {}}
        for arm in ("B", "F4"):
            job = jobmap[pid, arm]
            answer = success[job["request_id"]]
            rp = ROOT / answer["receipt_source"]
            receipt = run084.read(rp)
            tr = receipt["transport"]
            parsed = parse_response(tr, True, True)
            assert parsed.get("model_returned") == run084.MODEL
            valid = parsed["status"] in VALID and parsed.get("scores") is not None
            fallback = x["fallback_U2"]
            native = json.loads(tr["body_text"])
            message = native["choices"][0]["message"]
            content = message.get("content")
            try:
                content_obj = json.loads(content) if isinstance(content, str) else None
            except (ValueError, TypeError):
                content_obj = None
            native_manifest.append({"id": pid, "sid": sid, "arm": arm, "request_id": job["request_id"],
                                    "body_sha256": job["body_sha256"], "receipt_source": answer["receipt_source"],
                                    "receipt_sha256": run084.sha(rp), "model": native.get("model"),
                                    "response_id": native.get("id"), "finish_reason": native["choices"][0].get("finish_reason"),
                                    "verdict": content_obj.get("verdict") if isinstance(content_obj, dict) else None,
                                    "scores": content_obj.get("label_scores") if isinstance(content_obj, dict) else None,
                                    "reason": content_obj.get("reason") if isinstance(content_obj, dict) else None,
                                    "checks": content_obj.get("checks") if isinstance(content_obj, dict) else None,
                                    "reasoning_content": message.get("reasoning_content"), "usage": native.get("usage")})
            row["arms"][arm] = {"status": parsed["status"], "valid": valid,
                                "raw": parsed.get("verdict"), "scores": parsed.get("scores"),
                                "reason_present": bool(content_obj.get("reason")) if isinstance(content_obj, dict) else False,
                                "checks_present": bool(content_obj.get("checks")) if isinstance(content_obj, dict) else False,
                                "reasoning_present": parsed.get("reasoning_present"),
                                "body_sha256": job["body_sha256"], "receipt_source": answer["receipt_source"],
                                "usage": parsed.get("usage"), "elapsed_seconds": tr.get("client_elapsed_seconds")}
            if not valid:
                invalid.append({"id": pid, "sid": sid, "arm": arm, "status": parsed["status"],
                                "fallback": fallback, "finish_reason": parsed.get("finish_reason")})
            row["methods"][arm] = {"raw": parsed["verdict"] if valid else fallback,
                                   "U0": decision(parsed["scores"], 0) if valid else fallback,
                                   "U2": decision(parsed["scores"], 2) if valid else fallback,
                                   "PriorG": priorg(parsed["scores"]) if valid else fallback}
        rows.append(row)
    assert len(rows) == 180
    write_lines(OUT / "new_predictions.jsonl", rows)
    write_lines(OUT / "native_manifest.jsonl", native_manifest)
    write_json(OUT / "new_invalid.json", invalid)
    return rows, attempts, gtsha


def historical():
    old = lines(ROOT / "outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl")
    assert len(old) == 532 and len({x["id"] for x in old}) == 532
    return old


def cohort(rows):
    return [{"proposition_id": x["id"], "subject_id": x["sid"], "human_gt": x["GT"]} for x in rows]


def pred(rows, config, method):
    if config == "original":
        return [{"proposition_id": x["id"], "verdict": x["original_verifact"]} for x in rows]
    return [{"proposition_id": x["id"], "verdict": x["methods"][config][method]} for x in rows]


def metric(rows, config, method, bootstrap=True):
    ev = evaluate(cohort(rows), pred(rows, config, method),
                  profile="research_patient" if bootstrap else "none", missing="error", iterations=1000)
    label = lambda x: x["original_verifact"] if config == "original" else x["methods"][config][method]
    nons = sum(x["GT"] != LABELS[0] for x in rows)
    return {"config": config, "method": method, "n": len(rows), "patients": len({x["sid"] for x in rows}),
            "correct": sum(x["GT"] == label(x) for x in rows), "PA": ev["percent_agreement"],
            "MCC": ev["mcc"], "AC1": ev["gwet_ac1"],
            "macro_F1": statistics.mean((ev["per_class"][k]["f1"] or 0) for k in LABELS),
            "false_S": sum(x["GT"] != LABELS[0] and label(x) == LABELS[0] for x in rows),
            "nonS_denominator": nons, "false_S_rate_nonS": sum(x["GT"] != LABELS[0] and label(x) == LABELS[0] for x in rows) / nons if nons else None,
            "confusion_matrix": ev["confusion_matrix"], "per_class": ev["per_class"],
            "CI95": ev.get("confidence_intervals"), "coverage": ev["coverage"]}


def false_s_ci(rows, method, seed):
    groups = defaultdict(list)
    for x in rows:
        groups[x["sid"]].append(x)
    patients = sorted(groups)
    rng = random.Random(seed)
    values = []
    for _ in range(1000):
        drawn = [x for sid in rng.choices(patients, k=len(patients)) for x in groups[sid]]
        nons = sum(x["GT"] != LABELS[0] for x in drawn)
        if nons == 0:
            continue
        rate = lambda arm: sum(x["GT"] != LABELS[0] and x["methods"][arm][method] == LABELS[0] for x in drawn) / nons
        values.append(rate("F4") - rate("B"))
    values.sort()
    if not values:
        return None
    return [values[int(.025 * (len(values) - 1))], values[int(.975 * (len(values) - 1))]]


def pair(rows, method, seed):
    ev = paired_compare(cohort(rows), pred(rows, "B", method), pred(rows, "F4", method), iterations=1000)
    rescued = [x for x in rows if x["methods"]["B"][method] != x["GT"] and x["methods"]["F4"][method] == x["GT"]]
    harmed = [x for x in rows if x["methods"]["B"][method] == x["GT"] and x["methods"]["F4"][method] != x["GT"]]
    patient_net = {sid: sum(int(x in rescued) - int(x in harmed) for x in rows if x["sid"] == sid) for sid in sorted({x["sid"] for x in rows})}
    nons = sum(x["GT"] != LABELS[0] for x in rows)
    fdelta = sum(int(x["GT"] != LABELS[0] and x["methods"]["F4"][method] == LABELS[0]) -
                 int(x["GT"] != LABELS[0] and x["methods"]["B"][method] == LABELS[0]) for x in rows)
    transitions = Counter((x["GT"], x["methods"]["B"][method], x["methods"]["F4"][method]) for x in rows)
    return {"method": method, "rescue": len(rescued), "harm": len(harmed), "net": len(rescued) - len(harmed),
            "rescue_ids": [x["id"] for x in rescued], "harm_ids": [x["id"] for x in harmed],
            "rescue_GT": dict(Counter(x["GT"] for x in rescued)), "harm_GT": dict(Counter(x["GT"] for x in harmed)),
            "patient_net": patient_net, "patient_wins": sum(n > 0 for n in patient_net.values()),
            "patient_losses": sum(n < 0 for n in patient_net.values()), "patient_ties": sum(n == 0 for n in patient_net.values()),
            "delta_false_S": fdelta, "delta_false_S_rate_nonS": fdelta / nons if nons else None,
            "delta_false_S_rate_nonS_CI95": false_s_ci(rows, method, seed),
            "GT_transitions": [{"GT": k[0], "B": k[1], "F4": k[2], "n": v} for k,v in sorted(transitions.items())],
            "metrics": ev["metrics"]}


def descriptive(rows, leave_mcc=False):
    patient = []
    for sid in sorted({x["sid"] for x in rows}):
        take = [x for x in rows if x["sid"] == sid]
        b = sum(x["methods"]["B"]["PriorG"] == x["GT"] for x in take)
        f = sum(x["methods"]["F4"]["PriorG"] == x["GT"] for x in take)
        patient.append({"sid": sid, "n": len(take), "human_n": sum(x["author"] == "human" for x in take),
                        "llm_n": sum(x["author"] == "llm" for x in take), "B_correct": b, "F4_correct": f,
                        "B_PA": b/len(take), "F4_PA": f/len(take), "delta_PA": (f-b)/len(take)})
    leave_mcc_values = {}
    if leave_mcc:
        for sid in sorted({x["sid"] for x in rows}):
            rest = [x for x in rows if x["sid"] != sid]
            leave_mcc_values[sid] = metric(rest, "F4", "PriorG", False)["MCC"] - metric(rest, "B", "PriorG", False)["MCC"]
    return {"patients": patient, "equal_patient_B_PA": statistics.mean(x["B_PA"] for x in patient),
            "equal_patient_F4_PA": statistics.mean(x["F4_PA"] for x in patient),
            "leave_one_patient_out_net": {x["sid"]: sum(y["F4_correct"]-y["B_correct"] for y in patient if y["sid"] != x["sid"]) for x in patient},
            "leave_one_patient_out_delta_MCC": leave_mcc_values}


def cost(attempts, rows):
    full = []
    for x in attempts:
        y = dict(x)
        y["created_utc"] = run084.read(ROOT / x["request_source"])["created_utc"]
        if x["receipt_source"]:
            tr = run084.read(ROOT / x["receipt_source"])["transport"]
            y["elapsed_seconds"] = tr.get("client_elapsed_seconds")
            if tr.get("http_status") == 200:
                native = json.loads(tr["body_text"])
                y["usage"] = native.get("usage")
                y["returned_model"] = native.get("model")
        full.append(y)
    full.sort(key=lambda x: (x["created_utc"], x["attempt_id"]))
    write_lines(OUT / "attempt_ledger.jsonl", full)
    total = sum(x["original_price_or_unknown_reserved_cny"] for x in attempts)
    assert total <= 20 + 1e-9
    arm = {}
    for side in ("B", "F4"):
        take = [x["arms"][side] for x in rows]
        usage = [x["usage"] for x in take]
        cost_arm = sum((u["prompt_tokens"]*3+u["completion_tokens"]*9)/1e6 for u in usage)
        arm[side] = {"n": len(take), "prompt_tokens": sum(u["prompt_tokens"] for u in usage),
                     "completion_tokens": sum(u["completion_tokens"] for u in usage),
                     "original_price_cny": cost_arm, "mean_original_per_case_cny": cost_arm/len(take),
                     "median_prompt_tokens": statistics.median(u["prompt_tokens"] for u in usage),
                     "median_completion_tokens": statistics.median(u["completion_tokens"] for u in usage),
                     "median_client_elapsed_seconds": statistics.median(x["elapsed_seconds"] for x in take),
                     "http200_core_invalid": sum(not x["valid"] for x in take)}
    result = {"hard_cap_cny": 20, "original_used_or_unknown_reserved_cny": total,
              "attempts": len(attempts), "http200": sum(x["http_status"] == 200 for x in attempts),
              "http0_unknown_or_reserved": sum(x["http_status"] in (None,0) for x in attempts),
              "arms": arm, "source": "Alibaba Cloud original busy-time ¥3/¥9 per million tokens; no discount",
              "cached_history_new_task_price_cny": 0}
    write_json(OUT / "cost_ledger.json", result)
    return result


def main():
    frozen = run084.read(OUT / "freeze.json")
    assert frozen["status"] == "FROZEN_BEFORE_FIRST_084_API_AND_GT"
    new, attempts, gtsha = new_records()
    old = historical()
    assert not {x["id"] for x in new} & {x["id"] for x in old}
    cohorts = {"new084": new, "old352": [x for x in old if x["cohort"] == "old352"],
               "old082new180": [x for x in old if x["cohort"] == "new180"],
               "historical532": old, "combined712": old+new}
    assert [len(cohorts[k]) for k in cohorts] == [180,352,180,532,712]
    metrics, pairs, detail = {}, {}, {}
    for name, take in cohorts.items():
        methods = [("original","published"), ("B","raw"), ("F4","raw"),
                   ("B","U0"), ("F4","U0"), ("B","U2"), ("F4","U2"),
                   ("B","PriorG"), ("F4","PriorG")]
        metrics[name] = [metric(take, arm, rule) for arm, rule in methods]
        pairs[name] = {rule: pair(take, rule, 8400+i) for i, rule in enumerate(("raw","U0","U2","PriorG"))}
        detail[name] = descriptive(take, name == "new084")
    strata = {}
    for field, values in (("author", ("human", "llm")),
                          ("material_sources", (("020",),("026",),("031",))),
                          ("full_candidate_pool_overlap", (False, True)),
                          ("teaching_candidate_patient_overlap", (False, True)),
                          ("teaching_exposure", (False, True))):
        for value in values:
            if field == "teaching_exposure":
                subset = [x for x in new if bool(x[field]) == value]
            elif field == "material_sources":
                subset = [x for x in new if tuple(x[field]) == value]
            else:
                subset = [x for x in new if x[field] == value]
            if subset:
                key = field + "=" + str(value)
                if len(subset) >= 20 and len({x["GT"] for x in subset}) == 3:
                    paired = pair(subset, "PriorG", 8421)
                else:
                    rescue = sum(x["methods"]["B"]["PriorG"] != x["GT"] and x["methods"]["F4"]["PriorG"] == x["GT"] for x in subset)
                    harm = sum(x["methods"]["B"]["PriorG"] == x["GT"] and x["methods"]["F4"]["PriorG"] != x["GT"] for x in subset)
                    paired = {"rescue": rescue, "harm": harm, "net": rescue-harm,
                              "note": "descriptive only: small n or missing GT class"}
                strata[key] = {"n": len(subset), "patients": len({x["sid"] for x in subset}),
                               "metrics": [metric(subset, a, "PriorG", False) for a in ("B", "F4")],
                               "paired": paired}
    valid = [x for x in new if all(x["arms"][a]["valid"] for a in ("B", "F4"))]
    shared = {"n": len(valid), "metrics": [metric(valid, a, "PriorG") for a in ("B","F4")],
              "paired": pair(valid, "PriorG", 8484)}
    c = cost(attempts, new)
    results = {"status": "EVALUATED_AFTER_FROZEN_084_API", "freeze_sha256": run084.sha(OUT / "freeze.json"),
               "GT_source_sha256": gtsha,
               "teaching_candidate_patient_source_sha256": run084.sha(ROOT / "outputs/071_judge_icl_feasibility/freeze.json"),
               "cohorts": {k:{"n":len(v),"patients":len({x["sid"] for x in v}),"GT":dict(Counter(x["GT"] for x in v))} for k,v in cohorts.items()},
               "metrics": metrics, "paired": pairs, "patient_details": detail,
               "strata_new084": strata, "new084_common_core_valid": shared,
               "new084_invalid": run084.read(OUT / "new_invalid.json"), "cost": c}
    write_json(OUT / "evaluation_results.json", results)
    print(json.dumps({"cohorts":results["cohorts"],"new_primary": [(x["config"],x["correct"],round(x["MCC"],4),x["false_S"]) for x in metrics["new084"] if x["method"] == "PriorG"],
                      "new_pair": {k:pairs["new084"]["PriorG"][k] for k in ("rescue","harm","net","delta_false_S")},
                      "cost": c["original_used_or_unknown_reserved_cny"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
