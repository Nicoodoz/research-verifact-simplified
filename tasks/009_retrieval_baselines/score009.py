"""Unified 002 metrics, completeness, transitions and task-wide native costs."""
from collections import Counter,defaultdict
from pathlib import Path
import argparse
import statistics
import study009 as s
from io009 import stage,old_judge_cache,normalize

MAIN=("A48","B48","C48")


def mean_or_none(values):
    values=list(values)
    return statistics.mean(values) if values else None


def movement(before,after,gt):
    if before is None or after is None:
        return "missing"
    if before==after:
        return "stable_correct" if before==gt else "stable_wrong"
    return "improved" if after==gt else "worsened" if before==gt else "changed_wrong"


def evaluate_scope(cohort,predictions,methods,contrasts):
    metrics={}
    for author in ("llm","human"):
        rows=[r for r in cohort if r["author_type"]==author]
        ids={r["proposition_id"] for r in rows}
        pp={a:[p for p in predictions[a] if p["proposition_id"] in ids] for a in methods}
        values={}
        for a in methods:
            missing=sorted(ids-{p["proposition_id"] for p in pp[a]})
            values[a]=dict(status="blocked_missing",expected_n=len(rows),missing_ids=missing) if missing or not rows else s.pilot.evaluate(rows,pp[a],iterations=1000)
        paired={}
        for before,after in contrasts:
            paired[after+"_minus_"+before]=dict(status="blocked_incomplete_pair") if any("status" in values[a] for a in (before,after)) else s.pilot.paired_compare(rows,pp[before],pp[after],iterations=1000)
        metrics[author]=dict(metrics=values,contrasts=paired)
    return metrics


def score(folder,phase,output):
    folder,output=folder.resolve(),output.resolve()
    assert not (s.OUT/"live"/phase/"runner.lock").exists(),"Execution still active; wait for terminal stage state"
    cohort=s.pilot.read_csv(folder/"preparation/cohort.csv")[1]
    cidx={r["proposition_id"]:r for r in cohort}
    s.check(folder/"judge_preparation")
    inputs={x["proposition_id"]:x for x in s.pilot.jsonl(folder/"judge_preparation/inputs.jsonl")}
    assignments=s.pilot.read_csv(folder/"judge_preparation/assignments.csv")[1]
    values,attempts=stage(phase)
    repeat=s.read_json(folder/"judge_preparation/repeats.json")
    pids={a["request_id"]:a["proposition_id"] for a in assignments if a["request_id"]}
    pids.update({r["request_id"]:r["proposition_id"] for r in repeat})
    for r in repeat:
        pids[r["canonical_request_id"]]=r["proposition_id"]
    normalized={rid:dict(normalize(v["job"],v["receipt"],pids[rid]),origin=phase) for rid,v in values.items()}
    cachefile=folder/"judge_preparation/cache_bindings.json"
    if cachefile.exists():
        cache=old_judge_cache()
        for sha,binding in s.read_json(cachefile).items():
            old=cache[sha]
            assert s.pilot.digest_file(s.ROOT/binding["receipt_path"])==binding["receipt_sha256"]
            rid=old["request_id"]
            normalized[rid]=dict(normalize(dict(request_id=rid,body=old["body"]),old["receipt"],pids[rid]),origin="008_cached_not_billed_to_009")
    methods=sorted({a["method"] for a in assignments})
    predictions={a:[] for a in methods}
    lookup={a:{} for a in methods}
    for a in assignments:
        result=normalized.get(a["request_id"],{})
        if result.get("status")=="success":
            predictions[a["method"]].append(dict(proposition_id=a["proposition_id"],verdict=result["verdict"]))
            lookup[a["method"]][a["proposition_id"]]=result["verdict"]
    metrics=evaluate_scope(cohort,predictions,MAIN,[("A48","B48"),("A48","C48"),("B48","C48")])
    diagnostic_methods=[a for a in ("A48","B48","C48","A80","B80","B48_no_rerank","B48_no_note_cap") if a in methods]
    diagnostic_ids={a["proposition_id"] for a in assignments if a["method"]=="B80"}
    diagnostic={}
    if diagnostic_ids:
        own=[r for r in cohort if r["proposition_id"] in diagnostic_ids]
        diagnostic=evaluate_scope(own,predictions,diagnostic_methods,[("A48","A80"),("B48","B80"),("B48_no_rerank","B48"),("B48","B48_no_note_cap"),("A80","B80")])
    common=set(cidx)
    for method in MAIN:
        common &=set(lookup[method])
    sensitivity=dict(required=len(common)!=len(cohort),original_n=len(cohort),complete_triplet_n=len(common),
        excluded_ids=sorted(set(cidx)-common),status="not_needed")
    if len(common)!=len(cohort):
        own=[r for r in cohort if r["proposition_id"] in common]
        sensitivity["status"]="explicit_common_complete_sensitivity_not_primary"
        if all(len({r["subject_id"] for r in own if r["author_type"]==a})>=2 for a in ("llm","human")):
            sensitivity["metrics"]=evaluate_scope(own,predictions,MAIN,[("A48","B48"),("A48","C48"),("B48","C48")])
        else:
            sensitivity["status"]="too_few_patients_for_complete_triplet_bootstrap"
    transitions=[]
    for row in cohort:
        pid=row["proposition_id"]
        labels={method:lookup[method].get(pid) for method in MAIN}
        transitions.append(dict(row,case_id=inputs[pid]["case_id"],**labels,
            B_minus_A=movement(labels["A48"],labels["B48"],row["human_gt"]),
            C_minus_A=movement(labels["A48"],labels["C48"],row["human_gt"]),
            C_minus_B=movement(labels["B48"],labels["C48"],row["human_gt"])))
    patient=[]
    for sid in sorted({r["subject_id"] for r in cohort}):
        for author in ("llm","human"):
            rows=[r for r in cohort if r["subject_id"]==sid and r["author_type"]==author]
            ids={r["proposition_id"] for r in rows}
            for method in MAIN:
                pred=[r for r in predictions[method] if r["proposition_id"] in ids]
                value=s.pilot.evaluate(rows,pred,profile="none") if len(pred)==len(rows) and rows else dict(status="blocked")
                patient.append(dict(subject_id=sid,author_type=author,method=method,**value))
    repetition=[]
    for r in repeat:
        first,second=normalized[r["canonical_request_id"]],normalized[r["request_id"]]
        if first.get("status")==second.get("status")=="success":
            assert first["request_sha256"]==second["request_sha256"]==r["body_sha256"]
        repetition.append(dict(r,canonical_status=first["status"],repeat_status=second["status"],canonical_verdict=first.get("verdict"),repeat_verdict=second.get("verdict"),
            changed=first.get("verdict")!=second.get("verdict"),diagnostic_only=True))
    retrieval=[]
    for a in assignments:
        if a["status"]!="ready":
            continue
        item=inputs[a["proposition_id"]]
        r=item["retrieval"][a["method"]]
        first=item["retrieval"]["A48"]
        reply=normalized[a["request_id"]]
        retrieval.append(dict(proposition_id=a["proposition_id"],case_id=item["case_id"],subject_id=item["subject_id"],author_type=item["author_type"],method=a["method"],
            candidates=len(r["candidate_ids"]),selected=len(r["selected_ids"]),reference_characters=len(r["reference"]),body_characters=r["body_characters"],
            new_selected_vs_A=len(set(r["selected_ids"])-set(first.get("selected_ids",[]))),lost_selected_vs_A=len(set(first.get("selected_ids",[]))-set(r["selected_ids"])),
            same_body_as_A=r["body_sha256"]==first.get("body_sha256"),input_tokens=reply.get("usage",{}).get("input_tokens"),output_tokens=reply.get("usage",{}).get("output_tokens"),
            skip_counts=dict(Counter(x["reason"] for x in r["selection_skips"]))))
    summary=dict(claims=len(cohort),valid_predictions={m:len(predictions[m]) for m in methods},
        failures=[dict(request_id=rid,status=r["status"],errors=r["structural_errors"]) for rid,r in normalized.items() if r["status"]!="success"],
        transitions={a:{key:dict(Counter(r[key] for r in transitions if r["author_type"]==a)) for key in ("B_minus_A","C_minus_A","C_minus_B")} for a in ("llm","human")},
        repeat_pairs=len(repetition),repeat_changes=sum(x["changed"] for x in repetition),
        exact_A_bodies={a:sum(x["same_body_as_A"] for x in retrieval if x["method"]==a) for a in MAIN},
        mean_reference_characters={a:mean_or_none(x["reference_characters"] for x in retrieval if x["method"]==a) for a in MAIN},
        mean_input_tokens={a:mean_or_none(x["input_tokens"] for x in retrieval if x["method"]==a and x["input_tokens"] is not None) for a in MAIN},
        costs_this_phase=sum(x["charge_cny"] for x in attempts),independent_audit=False)
    output.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(output/"metrics.json",metrics)
    s.pilot.write_json(output/"diagnostic_metrics.json",diagnostic)
    s.pilot.write_json(output/"completeness_sensitivity.json",sensitivity)
    s.pilot.write_jsonl(output/"normalized_responses.jsonl",list(normalized.values()))
    s.pilot.write_csv(output/"transitions.csv",transitions)
    s.pilot.write_json(output/"patient_metrics.json",patient)
    s.pilot.write_json(output/"repeat_diagnostics.json",repetition)
    s.pilot.write_jsonl(output/"retrieval_diagnostics.jsonl",retrieval)
    s.pilot.write_csv(output/"attempts.csv",attempts)
    for method in methods:
        s.pilot.write_csv(output/("predictions_"+method+".csv"),predictions[method],fields=["proposition_id","verdict"])
    s.pilot.write_json(output/"summary.json",summary)
    s.seal(output,[folder/"judge_preparation/manifest.json",folder/"preparation/manifest.json",s.OUT/"live"/phase/"state.json"],
        [s.TASK/"score009.py",s.TASK/"io009.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    p.add_argument("phase",choices=("dev_judge","confirm_judge"))
    p.add_argument("--output",type=Path)
    a=p.parse_args()
    score(a.folder,a.phase,a.output or a.folder/"analysis_001")
