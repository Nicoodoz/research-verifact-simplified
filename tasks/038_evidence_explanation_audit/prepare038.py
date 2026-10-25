"""Freeze 038 blind audit cohort and paid jobs. No API calls."""
import json
from pathlib import Path
import common038 as c

R036 = c.ROOT / "outputs" / "036_final_validation"
OUT = c.OUT / "planning_001"

def main():
    c.require(not OUT.exists(), "planning_001 already exists")
    OUT.mkdir(parents=True)
    rows = c.csvread(R036 / "analysis_001" / "R0" / "predictions.csv")
    c.require(len(rows) == 3571, "unexpected 036 common cohort")
    byid = {r["id"]: r for r in rows}

    score_jobs = {}
    for j in c.jsonl(R036 / "judge_inputs_001" / "jobs.jsonl"):
        if j.get("round") == "R0" and j.get("role") == "score":
            score_jobs[j["proposition_id"]] = j
    score_norm = {}
    for r in c.jsonl(R036 / "predictions_blind_001" / "normalized.jsonl"):
        if r.get("round") == "R0" and r.get("role") == "score":
            score_norm[r["proposition_id"]] = r
    c.require(set(byid) <= set(score_jobs) and set(byid) <= set(score_norm), "missing source score rows")
    flips = [r for r in rows if r["U0"] != "Supported" and r["U2"] == "Supported"]
    c.require(len(flips) == 342, "unexpected flip count")
    controls = []
    for label in c.LABELS:
        pool = [r for r in rows if r["Score_verdict"] == label and r["U0"] == label and r["U2"] == label]
        pool.sort(key=lambda r: c.stable_hash("038/control/v1:", r["id"]))
        c.require(len(pool) >= 40, "insufficient stable control " + label)
        controls.extend([(r, "control_" + label.replace(" ", "_")) for r in pool[:40]])

    blind = []
    for r in flips:
        blind.append(dict(id=r["id"], sid=r["sid"], author=r["author"], audit_group="U0_to_U2_S"))
    for r, group in controls:
        blind.append(dict(id=r["id"], sid=r["sid"], author=r["author"], audit_group=group))
    c.require(len(blind) == 462 and len({r["id"] for r in blind}) == 462, "blind cohort identity")
    c.csvwrite(OUT / "blind_cohort.csv", blind)

    keys = []
    for b in blind:
        r = byid[b["id"]]
        if b["audit_group"] == "U0_to_U2_S":
            if r["GT"] == "Supported": flip_type = "R"
            elif r["U0"] == r["GT"]: flip_type = "H"
            else: flip_type = "W"
        else:
            flip_type = ""
        keys.append(dict(**b, GT=r["GT"], Score_verdict=r["Score_verdict"], U0=r["U0"], U2=r["U2"],
                         Gate_A=r["Gate_A"], Std_M=r["Std_M"], Std_V=r["Std_V"], flip_type=flip_type))
    c.csvwrite(OUT / "evaluation_key.csv", keys)
    jobs = []
    for b in blind:
        src = score_jobs[b["id"]]
        payload = json.loads(src["body"]["messages"][1]["content"])
        c.require(set(payload) == {"proposition", "reference"}, "unexpected score payload")
        for mk in ("qwen", "deepseek"):
            model = c.MODELS[mk]
            jobs.append(dict(request_id=f"038_ev_{mk}_{b['id']}", kind="evidence", model_key=mk,
                             proposition_id=b["id"], audit_group=b["audit_group"],
                             body=c.evidence_body(payload["proposition"], payload["reference"], model)))

    reason_ids = [r["id"] for r in rows if r["U2"] == "Supported" and r["Score_verdict"] != "Supported"]
    c.require(len(reason_ids) == 346, "unexpected reason mismatch count")
    for pid in reason_ids:
        p = score_norm[pid]["parsed"]["parsed"]
        jobs.append(dict(request_id=f"038_reason_qwen_{pid}", kind="reason", model_key="qwen",
                         proposition_id=pid, audit_group="U2_S_reason_mismatch",
                         body=c.reason_body("Supported", p["verdict"], p.get("reason"), p.get("checks"), c.MODELS["qwen"])))

    estimate = sum(c.bound(j) for j in jobs)
    c.require(estimate <= c.CAP, f"planned conservative reservation {estimate:.3f} exceeds cap {c.CAP}")
    with (OUT / "jobs.jsonl").open("x", encoding="utf-8", newline="\n") as f:
        for j in jobs: f.write(json.dumps(j, ensure_ascii=False, sort_keys=True) + "\n")
    mismatch = []
    methods = ["U0","U2","U2_T","Gate_A","Std_T","Std_G","Std_M","Std_V","Joint_NLL","Task_T","Robust_T","MCC_T","U4"]
    for m in methods:
        n = sum(r[m] != r["Score_verdict"] for r in rows)
        fs = sum(r[m] == "Supported" and r["Score_verdict"] != "Supported" for r in rows)
        mismatch.append(dict(method=m, final_vs_score_verdict=n, final_S_vs_nonS_reason_source=fs))
    c.csvwrite(OUT / "label_reason_mismatch_counts.csv", mismatch)

    sources = [
        R036 / "analysis_001" / "R0" / "predictions.csv",
        R036 / "judge_inputs_001" / "jobs.jsonl",
        R036 / "predictions_blind_001" / "normalized.jsonl",
    ]
    c.put(OUT / "preflight.json", dict(
        created_utc=c.now(), common_n=len(rows), flips=len(flips), controls=120,
        evidence_cases=len(blind), reason_cases=len(reason_ids), jobs=len(jobs),
        conservative_reservation_cny=estimate, cap_cny=c.CAP,
        source_sha256={str(p.relative_to(c.ROOT)): c.file_hash(p) for p in sources},
        note="Evidence job bodies contain claim+C48 only; GT/method/reason withheld."
    ))
    print("038 frozen", len(jobs), "jobs; conservative reservation CNY", round(estimate, 3))

if __name__ == "__main__":
    main()
