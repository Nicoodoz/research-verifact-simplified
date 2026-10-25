"""Freeze 084 patient-rounded IDs and exact B/F4 bodies before new responses."""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"
sys.path.insert(0, str(ROOT / "tasks/082_anchor_configuration_adaptation"))
import prepare082 as p

LABELS = ("Supported", "Not Supported", "Not Addressed")


def read(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8-sig"))


def lines(rel):
    return [json.loads(s) for s in (ROOT / rel).open(encoding="utf-8-sig") if s.strip()]


def sha(rel):
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def stable(prefix, value):
    return hashlib.sha256((prefix + str(value)).encode()).hexdigest()


def write(name, data):
    path = OUT / name
    with path.open("x", encoding="utf-8", newline="\n") as f:
        if isinstance(data, list):
            for row in data:
                f.write(p.canonical(row) + "\n")
        else:
            f.write(p.canonical(data) + "\n")


def main():
    eligible_rel = "outputs/084_f4_coverage_validation/eligible_blind.jsonl"
    eligible = lines(eligible_rel)
    bysid = defaultdict(list)
    for x in eligible:
        assert not x["mechanism_exposure"] and x["sid"] != "85689"
        bysid[x["sid"]].append(x)
    assert len(bysid) == 21 and all(len(v) >= 9 for v in bysid.values())
    for sid in bysid:
        bysid[sid].sort(key=lambda x: (stable("084/sample/v1:", x["id"]), x["id"]))
    prior_new = {x["sid"] for x in lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")}
    assert len(prior_new) == 7
    extra_pool = sorted(set(bysid) - prior_new, key=lambda sid: (stable("084/extra-patient/v1:", sid), sid))
    assert len(extra_pool) == 15  # 85689 is in prior_new but unavailable for new clean IDs.
    extra_patients = set(extra_pool[:12])
    chosen = {sid: bysid[sid][:8 + int(sid in extra_patients)] for sid in bysid}
    sample = []
    for rank in range(9):
        for sid in sorted(chosen, key=lambda s: (stable("084/patient-send/v1:", s), s)):
            if rank < len(chosen[sid]):
                x = chosen[sid][rank].copy()
                x["patient_rank"] = rank + 1
                sample.append(x)
    assert len(sample) == 180 and len({x["id"] for x in sample}) == 180
    source032 = {x["proposition_id"]: x for x in lines("outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl")}
    for x in sample:
        original = source032[x["id"]]
        assert x["reference"] == original["reference"] and x["claim"] == original["text"]
        x["fallback_U2"] = LABELS[original["u2"]]
    oldcal = lines("outputs/079_f4_priorg_adaptation/calibration_cases.jsonl")
    oldf4 = lines("outputs/079_f4_priorg_adaptation/main_jobs.jsonl")
    btemplate = oldcal[0]["B"]["body"]
    ftemplate = oldf4[0]["body"]
    oldtmpl = read("outputs/082_anchor_configuration_adaptation/templates_frozen.json")
    assert hashlib.sha256(btemplate["messages"][0]["content"].encode()).hexdigest() == oldtmpl["B_system_sha256"]
    assert hashlib.sha256(ftemplate["messages"][0]["content"].encode()).hexdigest() == oldtmpl["F4_system_sha256"]
    assert {k:v for k,v in btemplate.items() if k != "messages"} == {k:v for k,v in ftemplate.items() if k != "messages"}
    old082 = lines("outputs/082_anchor_configuration_adaptation/eval_jobs.jsonl")
    compare = lines("outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl")[0]
    assert all(p.digest(p.score_body(template, compare["claim"], compare["reference"])) ==
               next(x["body_sha256"] for x in old082 if x["id"] == compare["id"] and x["arm"] == arm)
               for arm, template in (("B", btemplate), ("F4", ftemplate)))
    jobs = []
    for x in sample:
        first = ("B", "F4") if stable("084/arm-order/v1:", x["id"])[0] < "8" else ("F4", "B")
        for arm in first:
            template = btemplate if arm == "B" else ftemplate
            body = p.score_body(template, x["claim"], x["reference"])
            jobs.append({"request_id": f"084_main_{arm}_{x['id']}", "id": x["id"], "sid": x["sid"],
                         "arm": arm, "stage": "main", "body": body, "body_sha256": p.digest(body)})
    assert len(jobs) == 360 and len({x["request_id"] for x in jobs}) == 360
    write("sample_blind.jsonl", sample)
    write("main_jobs.jsonl", jobs)
    source_rels = (eligible_rel, "outputs/084_f4_coverage_validation/coverage_inventory.json",
        "tasks/084_f4_coverage_validation/protocol.md",
        "outputs/079_f4_priorg_adaptation/calibration_cases.jsonl",
        "outputs/079_f4_priorg_adaptation/main_jobs.jsonl",
        "outputs/082_anchor_configuration_adaptation/templates_frozen.json",
        "outputs/082_anchor_configuration_adaptation/eval_new_blind.jsonl",
        "outputs/082_anchor_configuration_adaptation/eval_jobs.jsonl",
        "outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl")
    price = {"provider": "Alibaba Cloud Beijing", "model": "deepseek-v4-flash-0731",
             "source": "https://help.aliyun.com/en/model-studio/model-pricing",
             "checked_utc": "2026-09-26T03:03:09Z", "original_busy_input_cny_per_million": 3,
             "original_busy_output_cny_per_million": 9, "discounts_ignored": True}
    freeze = {"status": "FROZEN_BEFORE_FIRST_084_API_AND_GT", "cap_original_cny": 20.0,
              "new_n": len(sample), "patients": sorted(chosen), "per_patient": dict(Counter(x["sid"] for x in sample)),
              "previously_082_new_patients": sorted(prior_new), "extra_patients": sorted(extra_patients),
              "excluded_85689": "8 remaining IDs all in 066-070/081 mechanism queues",
              "main_role": "new same-batch complete B/F4 pairs; no historical B/F4 exact answer IDs",
              "fallback_rule": "032 frozen nonthinking C48 U2 for HTTP200 core-invalid only, both arms same",
              "retry_rule": "maximum 3 attempts for communication failures; never retry HTTP200 content-invalid",
              "selection_uses_GT": False, "template_B_system_sha256": oldtmpl["B_system_sha256"],
              "template_F4_system_sha256": oldtmpl["F4_system_sha256"],
              "sample_sha256": sha("outputs/084_f4_coverage_validation/sample_blind.jsonl"),
              "jobs_sha256": sha("outputs/084_f4_coverage_validation/main_jobs.jsonl"),
              "source_sha256": {rel: sha(rel) for rel in source_rels}, "price": price,
              "forecast_original_cny": 14.04, "unknown_retry_length_buffer_cny": 5.96,
              "primary_metric": "delta MCC F4+Frozen PriorG minus B+Frozen PriorG",
              "PA_drop_tolerance_pp": 1.0, "false_S_nonS_rise_tolerance_pp": 3.0}
    write("freeze.json", freeze)
    print(json.dumps({"sample_n": len(sample), "patients": len(chosen), "jobs": len(jobs),
                      "source": {"+".join(k): v for k, v in Counter(tuple(x["material_sources"]) for x in sample).items()},
                      "teaching_exposure_n": sum(bool(x["teaching_exposure"]) for x in sample),
                      "candidate_pool_overlap_n": sum(x["full_candidate_pool_overlap"] for x in sample)}))


if __name__ == "__main__":
    main()
