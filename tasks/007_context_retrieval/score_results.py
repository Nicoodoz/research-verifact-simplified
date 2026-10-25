"""Offline original-GT evaluation, retrieval diagnostics and same-input comparisons."""
from collections import Counter, defaultdict
from datetime import datetime
import itertools
import json
from pathlib import Path
import statistics

import duckdb
import pandas as pd
import prepare as p
from retrieval import ARMS, tokens
from run_judge import charge_for, load_preparation


def normalize(job,item,transport):
    try:
        native=p.pilot.strict_json(transport["body_text"])
    except (ValueError,TypeError):
        native=None
    elapsed=(datetime.fromisoformat(transport["ended_utc"])-datetime.fromisoformat(transport["started_utc"])).total_seconds() if transport.get("ended_utc") and transport.get("started_utc") else 0
    arm,pid=job["request_id"].split(":",1)
    ref=item["retrieval"]["claim" if arm=="claim_repeat" else arm]["reference"]
    result=p.sf.normalize_result(dict(request_id=job["request_id"],proposition_id=pid,arm="structured",request_sha256=p.pilot.fingerprint(job["body"])),
        dict(reference=ref),dict(http_status=transport["http_status"],response_json=native,elapsed_seconds=elapsed,ended_utc=transport.get("ended_utc")),
        dict(judge=dict(model_id=p.sf.MODEL),generation=dict(max_output_tokens=2048),budget=dict(visible_explanation_word_limit=200)))
    result["arm"]=arm
    return result


def score(prep,run,output):
    jobs=load_preparation(prep)
    inputs={x["proposition_id"]:x for x in p.pilot.jsonl(prep/"inputs.jsonl")}
    cohort=p.pilot.read_csv(prep/"cohort.csv")[1]
    state=json.loads((run/"state.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True,exist_ok=False)
    normalized,attempts,failures=[],[],[]
    for job in jobs:
        progress=state["jobs"][job["request_id"]]
        for pointer in progress["receipts"]:
            path=run/pointer["file"]
            assert p.pilot.digest_file(path)==pointer["sha256"]
            receipt=json.loads(path.read_text(encoding="utf-8"))
            assert receipt["request_sha256"]==p.pilot.fingerprint(job["body"]) and receipt["request_id"]==job["request_id"] and receipt["run_id"]==state["run_id"]
            charge,basis=charge_for(receipt["transport"],job["max_cost_cny"])
            attempts.append(dict(request_id=job["request_id"],receipt_file=pointer["file"],sha256=pointer["sha256"],attempt=receipt["attempt"],account=receipt["account"],http_status=receipt["transport"]["http_status"],charge_cny=charge,charge_basis=basis))
        if progress["status"]=="response_received":
            assert receipt["transport"]["http_status"]==200
            result=normalize(job,inputs[job["request_id"].split(":",1)[1]],receipt["transport"])
            normalized.append(result)
            if result["status"]!="success":
                failures.append(dict(request_id=job["request_id"],kind="invalid_response",errors=result["structural_errors"]))
        else:
            failures.append(dict(request_id=job["request_id"],kind=progress["status"],attempts=progress["attempts"]))
    p.pilot.write_jsonl(output/"normalized_responses.jsonl",normalized)
    p.pilot.write_csv(output/"attempts.csv",attempts)
    preds={a:[dict(proposition_id=r["proposition_id"],verdict=r["verdict"]) for r in normalized if r["arm"]==a and r["status"]=="success"] for a in (*ARMS,"claim_repeat")}
    metrics={}
    for author in ("llm","human"):
        own=[r for r in cohort if r["author_type"]==author]
        ids={r["proposition_id"] for r in own}
        pp={a:[r for r in preds[a] if r["proposition_id"] in ids] for a in ARMS}
        mm={}
        for a in ARMS:
            missing=sorted(ids-{r["proposition_id"] for r in pp[a]})
            mm[a]=dict(status="blocked",missing_ids=missing,expected_n=len(own)) if missing else p.pilot.evaluate(own,pp[a],iterations=1000)
        comparisons={}
        for before,after in itertools.combinations(ARMS,2):
            comparisons[after+"_minus_"+before]=dict(status="blocked_incomplete_pair") if any(mm[a].get("status")=="blocked" for a in (before,after)) else p.pilot.paired_compare(own,pp[before],pp[after],iterations=1000)
        metrics[author]=dict(metrics=mm,contrasts=comparisons)
    p.pilot.write_json(output/"metrics.json",metrics)
    lookup={a:{r["proposition_id"]:r["verdict"] for r in v} for a,v in preds.items()}
    transitions=[dict(r,case_id=inputs[r["proposition_id"]]["case_id"],**{a:lookup[a].get(r["proposition_id"],"") for a in preds}) for r in cohort]
    p.pilot.write_csv(output/"transitions.csv",transitions)
    for a in ARMS:
        p.pilot.write_csv(output/("predictions_"+a+".csv"),preds[a],fields=["proposition_id","verdict"])
    same=[]
    body_groups=defaultdict(list)
    norm={r["request_id"]:r for r in normalized}
    for job in jobs:
        body_groups[p.pilot.fingerprint(job["body"])].append(job["request_id"])
    for key,group in body_groups.items():
        if len(group)>1:
            valid={rid:norm[rid]["verdict"] for rid in group if rid in norm and norm[rid]["status"]=="success"}
            same.append(dict(body_sha256=key,request_ids=group,valid_verdicts=valid,all_valid=len(valid)==len(group),labels_disagree=len(set(valid.values()))>1))
    p.pilot.write_json(output/"same_input_diagnostics.json",same)
    diagnostics=[]
    for item in inputs.values():
        claim_words={t for t in tokens(item["text"]) if not t.isdigit()}
        original_ids=set(item["retrieval"]["claim"]["reference_passage_ids"])
        for a in ARMS:
            result=item["retrieval"][a]
            own_ids=set(result["reference_passage_ids"])
            diagnostics.append(dict(case_id=item["case_id"],proposition_id=item["proposition_id"],author_type=item["author_type"],arm=a,
                reference_chars=len(result["reference"]),passage_count=len(result["passages"]),
                jaccard_passage_ids_with_claim=len(original_ids&own_ids)/max(1,len(original_ids|own_ids)),
                passages_without_literal_claim_terms=sum(not(claim_words&set(tokens(x["text"]))) for x in result["passages"]),
                budget_truncated_passages=sum(x.get("display_truncated_for_budget",False) for x in result["passages"]),
                proxy_not_medical_relevance=True))
    p.pilot.write_csv(output/"retrieval_diagnostics.csv",diagnostics)
    summary=dict(expected_requests=len(jobs),received=len(normalized),valid=sum(r["status"]=="success" for r in normalized),failures=failures,
        settled_and_reserved_cny=sum(r["charge_cny"] for r in attempts),state_budget_cny=state["reserved_budget_cny"],invoice_verified=False,
        by_arm={a:dict(received=sum(r["arm"]==a for r in normalized),valid=len(preds[a]),
            input_tokens=sum(r.get("usage",{}).get("input_tokens",0) for r in normalized if r["arm"]==a),
            output_tokens=sum(r.get("usage",{}).get("output_tokens",0) for r in normalized if r["arm"]==a),
            adherence_flags=dict(Counter(e for r in normalized if r["arm"]==a for e in r["adherence_errors"]))) for a in preds},
        identical_body_groups=len(same),identical_body_groups_with_label_disagreement=sum(x["labels_disagree"] for x in same),
        time_metadata_conflicts=sum(r["time_metadata_conflict"]=="True" for r in cohort),
        no_gold_evidence_recall_claim=True,status="offline_scored_pending_semantic_review")
    p.pilot.write_json(output/"summary.json",summary)
    p.pilot.write_json(output/"manifest.json",dict(prep_manifest_sha256=p.pilot.digest_file(prep/"manifest.json"),
        state_sha256=p.pilot.digest_file(run/"state.json"),scorer_sha256=p.pilot.digest_file(Path(__file__)),
        receipts_sha256={r["receipt_file"]:r["sha256"] for r in attempts},
        output_sha256={x.name:p.pilot.digest_file(x) for x in output.iterdir() if x.is_file()}))
    print(p.pilot.canonical(summary))


def released_references(prep,output):
    inputs=p.pilot.jsonl(prep/"inputs.jsonl")
    ids=[x["proposition_id"] for x in inputs]
    with duckdb.connect(config={"threads":2,"memory_limit":"2GB"}) as con:
        con.register("selected",pd.DataFrame({"proposition_id":ids}))
        rows=con.execute("SELECT proposition_id,reference_id,verdict FROM read_parquet(?) JOIN selected USING(proposition_id) WHERE rater_alias='v1.1.0-rater-121'",[str(p.RAW/"verifact/verdicts.parquet")]).fetchall()
        con.register("refids",pd.DataFrame({"reference_id":sorted({x[1] for x in rows})}))
        refs=dict(con.execute("SELECT reference_id,reference FROM read_parquet(?) JOIN refids USING(reference_id)",[str(p.RAW/"verifact/reference_payloads.parquet")]).fetchall())
    assert len(rows)==len(inputs)
    output.mkdir(exist_ok=False)
    p.pilot.write_jsonl(output/"references.jsonl",[dict(proposition_id=pid,reference_id=rid,reference=refs[rid],released_verdict=v,
        historical_R1_not_same_judge_or_evidence_budget=True) for pid,rid,v in rows])
    p.pilot.write_json(output/"manifest.json",dict(reference_file_sha256=p.pilot.digest_file(output/"references.jsonl"),
        source_sha256={name:p.pilot.digest_file(p.RAW/"verifact"/name) for name in ("verdicts.parquet","reference_payloads.parquet")},paid_calls=0))
    print("Released reference links saved:",len(rows))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=["release","score"])
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    if args.mode=="release":
        released_references(p.OUT/"preparation_003",args.output or p.OUT/"release_comparison_001")
    else:
        score(p.OUT/"preparation_003",p.OUT/"run_001",args.output or p.OUT/"run_001/analysis")
