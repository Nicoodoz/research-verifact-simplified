"""Offline evaluation via 002, cost replay, evidence and generation diagnostics."""
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
import argparse
import statistics
import common as c
from build_stages import phase_data,seal
import planning_core as pc


def normalize(value,pid):
    job,tr=value["job"],value["receipt"]["transport"]
    data=c.pilot.strict_json(job["body"]["messages"][1]["content"])
    elapsed=(datetime.fromisoformat(tr["ended_utc"])-datetime.fromisoformat(tr["started_utc"])).total_seconds()
    return c.sf.normalize_result(dict(request_id=job["request_id"],proposition_id=pid,arm="structured",request_sha256=c.pilot.fingerprint(job["body"])),
        dict(reference=data["reference"]),dict(http_status=tr["http_status"],response_json=value["native"],elapsed_seconds=elapsed,ended_utc=tr["ended_utc"]),
        dict(judge=dict(model_id=c.CHAT_MODEL),generation=dict(max_output_tokens=2048),budget=dict(visible_explanation_word_limit=200)))


def transition(before,after,gt):
    if not before or not after:
        return "missing"
    if before==after:
        return "stable_correct" if before==gt else "stable_wrong"
    return "improved" if after==gt else "worsened" if before==gt else "changed_wrong"


def score(output):
    for name in ("preparation_001","plans_001","candidates_001","judge_preparation_001"):
        c.check_files(c.OUT/name)
    cohort=c.pilot.read_csv(c.OUT/"preparation_001/cohort.csv")[1]
    inputs={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"judge_preparation_001/inputs.jsonl")}
    assignments=c.pilot.read_csv(c.OUT/"judge_preparation_001/assignments.csv")[1]
    repeat_assignments=c.read_json(c.OUT/"judge_preparation_001/repeat_assignments.json")
    candidates={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"candidates_001/candidates.jsonl")}
    plans=c.pilot.jsonl(c.OUT/"plans_001/plans.jsonl")
    passages={x["passage_id"]:x for x in c.pilot.jsonl(c.OUT/"preparation_001/corpus.jsonl")}
    all_attempts=[]
    phases={}
    phase_values={}
    for phase in c.PHASE_CAPS:
        if not (c.OUT/"live"/phase).exists():
            assert phase=="embedding_plans" and not c.pilot.jsonl(c.OUT/"plans_001/embedding_jobs.jsonl")
            continue
        values,attempts=phase_data(phase)
        phase_values[phase]=values
        all_attempts+=attempts
        usage=Counter()
        for v in values.values():
            if v["job"]["kind"]=="chat":
                tokens=c.sf.normalize_usage(v["native"])
                usage.update({key:tokens[key] for key in ("input_tokens","output_tokens","reasoning_tokens")})
            else:
                native=v["native"]
                counted=native.get("usage",{}).get("prompt_tokens",native.get("meta",{}).get("billed_units",{}).get("input_tokens"))
                if counted is not None:
                    usage["input_tokens"]+=counted
        phases[phase]=dict(requests=len(values),attempts=len(attempts),estimated_or_reserved_cny=sum(x["charge_cny"] for x in attempts),
            usage=dict(usage),charge_bases=dict(Counter(x["charge_basis"] for x in attempts)),cap_cny=c.PHASE_CAPS[phase],invoice_verified=False)
    total=sum(v["estimated_or_reserved_cny"] for v in phases.values())
    assert total<=40
    job_pids={x["request_id"]:x["proposition_id"] for x in assignments+repeat_assignments}
    normalized={rid:normalize(value,job_pids[rid]) for rid,value in phase_values["judge"].items()}
    preds={arm:[] for arm in c.METHODS}
    for assignment in assignments:
        result=normalized[assignment["request_id"]]
        if result["status"]=="success":
            preds[assignment["method"]].append(dict(proposition_id=assignment["proposition_id"],verdict=result["verdict"]))
    lookup={a:{x["proposition_id"]:x["verdict"] for x in rows} for a,rows in preds.items()}
    metrics={}
    for author in ("llm","human"):
        own=[x for x in cohort if x["author_type"]==author]
        ids={r["proposition_id"] for r in own}
        ap={a:[x for x in pred if x["proposition_id"] in ids] for a,pred in preds.items()}
        mm={}
        for a in c.METHODS:
            missing=sorted(ids-{x["proposition_id"] for x in ap[a]})
            mm[a]=dict(status="blocked",missing_ids=missing,expected_n=len(own)) if missing else c.pilot.evaluate(own,ap[a],iterations=1000)
        contrasts={}
        for before,after in (("direct","planner"),("simple","planner"),("direct","simple")):
            contrasts[after+"_minus_"+before]=dict(status="blocked_incomplete_pair") if any(mm[a].get("status")=="blocked" for a in (before,after)) else c.pilot.paired_compare(own,ap[before],ap[after],iterations=1000)
        metrics[author]=dict(metrics=mm,contrasts=contrasts)
    transitions=[]
    for r in cohort:
        pid=r["proposition_id"]
        labels={a:lookup[a].get(pid,"") for a in c.METHODS}
        transitions.append(dict(r,case_id=inputs[pid]["case_id"],**labels,
            planner_vs_direct=transition(labels["direct"],labels["planner"],r["human_gt"]),
            planner_vs_simple=transition(labels["simple"],labels["planner"],r["human_gt"]),
            simple_vs_direct=transition(labels["direct"],labels["simple"],r["human_gt"])))
    patient_metrics=[]
    for sid in c.PATIENTS:
        for author in ("llm","human"):
            own=[r for r in cohort if r["subject_id"]==sid and r["author_type"]==author]
            ids={r["proposition_id"] for r in own}
            for arm in c.METHODS:
                part=[x for x in preds[arm] if x["proposition_id"] in ids]
                value=c.pilot.evaluate(own,part,profile="none") if len(part)==len(own) else dict(status="blocked")
                patient_metrics.append(dict(subject_id=sid,author_type=author,method=arm,**value))
    repeats=[]
    for r in repeat_assignments:
        first=normalized[r["canonical_request_id"]]
        second=normalized[r["request_id"]]
        assert first["request_sha256"]==second["request_sha256"]==r["body_sha256"]
        repeats.append(dict(r,canonical_status=first["status"],repeat_status=second["status"],canonical_verdict=first["verdict"],repeat_verdict=second["verdict"],
            label_changed=first["verdict"]!=second["verdict"],diagnostic_only=True))
    diagnostics=[]
    for pid,item in inputs.items():
        original=set(candidates[pid]["candidate_ids"]["direct"])
        direct_selected=set(item["retrieval"]["direct"]["selected_ids"])
        bm25=set(key for key,_ in candidates[pid]["query_rankings"][0]["bm25"][:48])
        for arm in c.METHODS:
            r=item["retrieval"][arm]
            pool=set(candidates[pid]["candidate_ids"][arm])
            selected=set(r["selected_ids"])
            result=normalized[r["request_id"]]
            claimwords={t for t in pc.tokenize(item["text"]) if not t.isdigit()}
            diagnostics.append(dict(proposition_id=pid,case_id=item["case_id"],subject_id=item["subject_id"],author_type=item["author_type"],method=arm,
                queries=len(candidates[pid]["queries"][arm]),candidates=len(pool),selected=len(selected),new_candidates=len(pool-original),lost_candidates=len(original-pool),
                new_selected=len(selected-direct_selected),lost_selected=len(direct_selected-selected),selected_outside_direct_candidates=len(selected-original),
                selected_outside_claim_bm25_top48=len(selected-bm25),reference_characters=len(r["reference"]),reference_words=len(r["reference"].split()),
                body_characters=r["body_characters"],input_tokens=result.get("usage",{}).get("input_tokens"),output_tokens=result.get("usage",{}).get("output_tokens"),
                selected_zero_claim_word_overlap=sum(not(claimwords&set(pc.tokenize(passages[k]["text"]))) for k in selected),
                same_direct_body=r["body_sha256"]==item["retrieval"]["direct"]["body_sha256"],
                skip_reasons=dict(Counter(x["reason"] for x in r["selection_skips"]))))
    summary=dict(label_meaning="Agreement with original independent-claim clinician labels, not new contextual GT",
        claims=len(cohort),valid_predictions={a:len(p) for a,p in preds.items()},unique_judge_requests=len(normalized),
        failed_judge_requests=[r for r,x in normalized.items() if x["status"]!="success"],
        adherence_diagnostic_requests=sum(bool(x["adherence_errors"]) for x in normalized.values()),
        transitions={author:{comparison:dict(Counter(r[comparison] for r in transitions if r["author_type"]==author)) for comparison in ("planner_vs_direct","planner_vs_simple","simple_vs_direct")} for author in ("llm","human")},
        repeat_pairs=len(repeats),repeat_label_changes=sum(x["label_changed"] for x in repeats),
        planner_status_by_author={a:dict(Counter(x["status"] for x in plans if inputs[x["proposition_id"]]["author_type"]==a)) for a in ("llm","human")},
        mean_actual_input_tokens={a:statistics.mean(x["input_tokens"] for x in diagnostics if x["method"]==a) for a in c.METHODS},
        mean_selected_passages={a:statistics.mean(x["selected"] for x in diagnostics if x["method"]==a) for a in c.METHODS},
        planner_new_selected_cases=sum(x["new_selected"]>0 for x in diagnostics if x["method"]=="planner"),
        planner_selected_outside_direct_pool_cases=sum(x["selected_outside_direct_candidates"]>0 for x in diagnostics if x["method"]=="planner"),
        total_estimated_or_reserved_cny=total,task_cap_cny=40,invoice_verified=False,independent_audit=False)
    output.mkdir(parents=True,exist_ok=False)
    c.pilot.write_json(output/"metrics.json",metrics)
    c.pilot.write_csv(output/"transitions.csv",transitions)
    c.pilot.write_jsonl(output/"normalized_responses.jsonl",list(normalized.values()))
    c.pilot.write_json(output/"patient_metrics.json",patient_metrics)
    c.pilot.write_json(output/"repeat_diagnostics.json",repeats)
    c.pilot.write_jsonl(output/"retrieval_diagnostics.jsonl",diagnostics)
    c.pilot.write_json(output/"costs.json",dict(phases=phases,total_estimated_or_reserved_cny=total,invoice_verified=False))
    c.pilot.write_csv(output/"attempts.csv",all_attempts)
    for arm in c.METHODS:
        c.pilot.write_csv(output/("predictions_"+arm+".csv"),preds[arm],fields=["proposition_id","verdict"])
    c.pilot.write_json(output/"summary.json",summary)
    deps=[c.OUT/x/"manifest.json" for x in ("preparation_001","plans_001","candidates_001","judge_preparation_001")]
    deps += [c.OUT/"live"/p/"state.json" for p in phase_values]
    seal(output,deps,code_files=[Path(__file__)])
    print(c.pilot.canonical(summary))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,default=c.OUT/"run_001/analysis")
    a=ap.parse_args()
    score(a.output)
