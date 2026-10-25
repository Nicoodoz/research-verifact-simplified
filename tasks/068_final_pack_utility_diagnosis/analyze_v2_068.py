"""Separate unified evaluation and stability analysis for 067's repaired v2 branch."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from analyze068 import ROOT, OUT, jsonl, load_receipts, metric_rows, false_s, save
from verifact_research.evaluation import evaluate, paired_compare


def main():
    p067 = ROOT / "outputs/067_conservative_evidence_packing"
    rows = list(csv.DictReader((p067 / "results_v2.csv").open(encoding="utf-8-sig", newline="")))
    assert len(rows) == 236 and len({row["id"] for row in rows}) == 236
    cohort = [{"proposition_id": row["id"], "subject_id": row["sid"], "human_gt": row["GT"]} for row in rows]
    unified = {}
    for stage, old_key, new_key in (("raw", "baseline_raw", "final_raw"), ("priorg", "baseline", "final")):
        base, final = metric_rows(rows, old_key), metric_rows(rows, new_key)
        unified[stage] = {
            "baseline": evaluate(cohort, base, profile="research_patient", missing="error", iterations=1000),
            "v2": evaluate(cohort, final, profile="research_patient", missing="error", iterations=1000),
            "paired": paired_compare(cohort, base, final, iterations=1000),
            "falseS_baseline": false_s(rows, old_key),
            "falseS_v2": false_s(rows, new_key),
        }
    save(OUT / "unified_evaluation_v2.json", unified)

    frozen = json.loads((OUT / "freeze_v2_068.json").read_text(encoding="utf-8"))
    v2_jobs = jsonl(OUT / "jobs_v2_068.jsonl")
    first_repeat = {job["request_id"]: job for job in jsonl(OUT / "jobs_002.jsonl")}
    all_jobs = v2_jobs + [first_repeat[rid] for rid in frozen["reused_exact_baseline_repeats"].values()]
    parsed = load_receipts(all_jobs)
    by_condition = {(job["id"], job["condition"]): parsed[job["request_id"]] for job in v2_jobs}
    result_by_id = {row["id"]: row for row in rows}
    details = []
    for pid in sorted({job["id"] for job in v2_jobs}):
        row = result_by_id[pid]
        old = parsed[frozen["reused_exact_baseline_repeats"][pid]] if pid in frozen["reused_exact_baseline_repeats"] else by_condition[(pid, "v2_baseline_repeat")]
        new = by_condition[(pid, "v2_final_repeat")]
        assert old["status"] == new["status"] == "valid"
        gt = row["GT"]
        historical = "rescue" if row["rescue"] == "True" else "harm" if row["harm"] == "True" else "unchanged"
        repeated = "rescue" if old["pg"] != gt and new["pg"] == gt else "harm" if old["pg"] == gt and new["pg"] != gt else "unchanged"
        repeated_raw = "rescue" if old["raw"] != gt and new["raw"] == gt else "harm" if old["raw"] == gt and new["raw"] != gt else "unchanged"
        details.append({
            "id": pid, "sid": row["sid"], "author": row["author"], "GT": gt,
            "historical_group": historical, "repeat_group": repeated, "repeat_raw_group": repeated_raw,
            "old_original_raw": row["baseline_raw"], "v2_original_raw": row["final_raw"],
            "old_original_pg": row["baseline"], "v2_original_pg": row["final"],
            "old_repeat_raw": old["raw"], "v2_repeat_raw": new["raw"],
            "old_repeat_pg": old["pg"], "v2_repeat_pg": new["pg"],
            "old_self_flip_raw": old["raw"] != row["baseline_raw"],
            "v2_self_flip_raw": new["raw"] != row["final_raw"],
            "old_self_flip_pg": old["pg"] != row["baseline"],
            "v2_self_flip_pg": new["pg"] != row["final"],
            "baseline_repeat_reused_from_v1_diagnosis": pid in frozen["reused_exact_baseline_repeats"],
        })
    with (OUT / "diagnostic_v2_cases.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for detail in details:
            handle.write(json.dumps(detail, ensure_ascii=False, sort_keys=True) + "\n")
    import run068
    attempts, done = run068.state()
    summary = {
        "v2_changed_n": len(details),
        "historical_groups": dict(Counter(x["historical_group"] for x in details)),
        "repeat_groups": dict(Counter(x["repeat_group"] for x in details)),
        "historical_to_repeat": {f"{a}->{b}": n for (a, b), n in Counter((x["historical_group"], x["repeat_group"]) for x in details).items()},
        "self_flips": {key: sum(x[key] for x in details) for key in ("old_self_flip_raw", "v2_self_flip_raw", "old_self_flip_pg", "v2_self_flip_pg")},
        "stable_rescue_patients": len({x["sid"] for x in details if x["historical_group"] == x["repeat_group"] == "rescue"}),
        "new_v2_jobs": len(v2_jobs),
        "baseline_reuses": len(frozen["reused_exact_baseline_repeats"]),
        "all_068_attempts": len(attempts),
        "all_068_http200": sum(x["http_status"] == 200 for x in attempts),
        "all_068_occupied_cny": sum(x["cost"] for x in attempts),
        "budget_cap_cny": 10.0,
        "reserved_used": False,
    }
    save(OUT / "analysis_v2_068.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
