"""Offline normalization and original-GT agreement for complete 006 pairs only."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path

import context_feasibility as cf
from run_context_pilot import charge_for,load_preparation


def normalize(job,item,transport):
    raw=transport["body_text"]
    try:
        native=cf.pilot.strict_json(raw)
    except (ValueError,TypeError):
        native=None
    elapsed=(datetime.fromisoformat(transport["ended_utc"])-datetime.fromisoformat(transport["started_utc"])).total_seconds() if transport.get("started_utc") and transport.get("ended_utc") else 0
    legacy=dict(http_status=transport["http_status"],response_json=native,elapsed_seconds=elapsed,ended_utc=transport.get("ended_utc"))
    arm,pid=job["request_id"].split(":",1)
    request=dict(request_id=job["request_id"],proposition_id=pid,arm="structured",request_sha256=cf.pilot.fingerprint(job["body"]))
    config=dict(judge=dict(model_id=cf.sf.MODEL),generation=dict(max_output_tokens=2048),budget=dict(visible_explanation_word_limit=200))
    result=cf.sf.normalize_result(request,item,legacy,config)
    result["arm"]=arm
    return result


def score(prep,run,output):
    jobs=load_preparation(prep)
    state=json.loads((run/"state.json").read_text(encoding="utf-8"))
    inputs={r["proposition_id"]:r for r in cf.pilot.jsonl(prep/"inputs.jsonl")}
    cohort=cf.pilot.read_csv(prep/"cohort.csv")[1]
    normalized=[]
    attempts=[]
    for job in jobs:
        progress=state["jobs"][job["request_id"]]
        cf.pilot.require(len(progress["receipts"])<=progress["attempts"],"More receipts than started attempts")
        for pointer in progress["receipts"]:
            path=run/pointer["file"]
            cf.pilot.require(cf.pilot.digest_file(path)==pointer["sha256"],"Receipt hash changed")
            receipt=json.loads(path.read_text(encoding="utf-8"))
            cf.pilot.require(receipt["request_sha256"]==cf.pilot.fingerprint(job["body"]) and receipt["request_id"]==job["request_id"],"Receipt request changed")
            charge,basis=charge_for(receipt["transport"],job["max_cost_cny"])
            attempts.append(dict(request_id=job["request_id"],account=receipt["account"],attempt=receipt["attempt"],
                http_status=receipt["transport"]["http_status"],estimated_cny=charge,charge_basis=basis,receipt_file=pointer["file"]))
        if progress["status"]=="response_received":
            receipt=json.loads((run/progress["receipts"][-1]["file"]).read_text(encoding="utf-8"))
            cf.pilot.require(receipt["transport"]["http_status"]==200 and receipt["attempt"]==progress["attempts"],"State/last response mismatch")
            pid=job["request_id"].split(":",1)[1]
            normalized.append(normalize(job,inputs[pid],receipt["transport"]))
    output.mkdir(parents=True,exist_ok=False)
    cf.pilot.write_jsonl(output/"normalized_responses.jsonl",normalized)
    cf.pilot.write_csv(output/"attempts.csv",attempts)
    predictions={a:[dict(proposition_id=r["proposition_id"],verdict=r["verdict"]) for r in normalized if r["arm"]==a and r["status"]=="success"] for a in cf.ARMS}
    for a in cf.ARMS:
        cf.pilot.write_csv(output/("predictions_"+a+".csv"),predictions[a],fields=["proposition_id","verdict"])
    results={}
    for author in ("llm","human"):
        rows=[r for r in cohort if r["author_type"]==author]
        ids={r["proposition_id"] for r in rows}
        pp={a:[p for p in predictions[a] if p["proposition_id"] in ids] for a in cf.ARMS}
        metrics={}
        contrasts={}
        for a in cf.ARMS:
            missing=sorted(ids-{p["proposition_id"] for p in pp[a]})
            metrics[a]=dict(status="blocked",missing_ids=missing,expected_n=len(rows)) if missing else cf.pilot.evaluate(rows,pp[a],iterations=1000)
        for baseline,candidate in (("structured","source_context"),("repeat_claim","source_context"),("structured","repeat_claim")):
            key=candidate+"_minus_"+baseline
            if any(metrics[a].get("status")=="blocked" for a in (baseline,candidate)):
                contrasts[key]=dict(status="blocked_incomplete_pair")
            else:
                contrasts[key]=cf.pilot.paired_compare(rows,pp[baseline],pp[candidate],iterations=1000)
        results[author]=dict(metrics=metrics,contrasts=contrasts)
    cf.pilot.write_json(output/"metrics.json",results)
    lookup={a:{p["proposition_id"]:p["verdict"] for p in predictions[a]} for a in cf.ARMS}
    cf.pilot.write_csv(output/"transitions.csv",[dict(r,**{a:lookup[a].get(r["proposition_id"],"") for a in cf.ARMS}) for r in cohort])
    summary=dict(valid_responses=len(sum(predictions.values(),[])),expected_responses=len(jobs),
        estimated_cny=sum(r["estimated_cny"] for r in attempts),invoice_verified=False,
        budget_used_or_reserved_cny=state["reserved_budget_cny"],
        unreceipted_attempts=sum(r["attempts"]-len(r["receipts"]) for r in state["jobs"].values()),
        raw_source_is_not_gold=True,label_meaning="Original independent-claim GT agreement; not contextual clinical correctness",
        failures=[dict(request_id=r["request_id"],errors=r["structural_errors"]) for r in normalized if r["status"]!="success"],
        status="scored_complete_pairs_only_pending_semantic_review")
    cf.pilot.write_json(output/"summary.json",summary)
    cf.pilot.write_json(output/"manifest.json",dict(preparation_manifest_sha256=cf.pilot.digest_file(prep/"manifest.json"),
        scorer_sha256=cf.pilot.digest_file(Path(__file__)),state_sha256=cf.pilot.digest_file(run/"state.json"),
        source_receipts_sha256={r["receipt_file"]:cf.pilot.digest_file(run/r["receipt_file"]) for r in attempts},
        output_sha256={p.name:cf.pilot.digest_file(p) for p in output.iterdir() if p.is_file()}))
    print(cf.pilot.canonical(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preparation",type=Path,required=True)
    p.add_argument("--run",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    score(a.preparation.resolve(),a.run.resolve(),a.output.resolve())
