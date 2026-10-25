"""Freeze all development evidence and Judge jobs from actually scored candidates."""
from collections import Counter
from pathlib import Path
import study009 as s
from io009 import stage,old_judge_cache,rerank_scores


def build():
    prep=s.OUT/"development_001/preparation"
    s.check(prep)
    values,_=stage("dev_embed")  # Registered rerank refresh, within the existing .25 slot.
    inputs=s.pilot.jsonl(prep/"inputs.jsonl")
    corpus=s.pilot.jsonl(prep/"corpus.jsonl")
    passages={x["passage_id"]:x for x in corpus}
    prompts=s.read_json(prep/"judge_prompts.json")
    old_cache=old_judge_cache()
    previous={x["proposition_id"]:x for x in s.pilot.jsonl(s.PRIOR/"judge_preparation_001/inputs.jsonl")}
    sentinel=s.read_json(s.OUT/"rerank_drift_001/pairs.json")
    scored={}
    failures=[]
    for item in inputs:
        pid=item["proposition_id"]
        rid="dev_refresh:"+pid
        scores={}
        if rid in values:
            try:
                fresh=rerank_scores(values[rid])
                scores=fresh
            except (AssertionError,KeyError,TypeError,ValueError) as e:
                failures.append(dict(proposition_id=pid,error=str(e)))
        scored[pid]=scores
    outputs,assignments,jobs,cached={},[],{},{}
    for item in inputs:
        pid=item["proposition_id"]
        results={}
        for name,config in item["variants"].items():
            scores=dict(item["rankings"]["dense"]) if config["order"]=="dense_cosine" else scored[pid]
            missing=sorted(set(config["candidate_ids"])-set(scores))
            if missing:
                results[name]=dict(status="blocked_missing_pair_scores",missing_ids=missing)
                assignments.append(dict(proposition_id=pid,case_id=item["case_id"],method=name,status="missing_evidence",source="",request_id="",body_sha256=""))
                continue
            selection=s.core.select_evidence(config["candidate_ids"],scores,passages,item["admission"],max_per_note=config["max_per_note"])
            body=s.prior_stages.judge_body(item,selection["reference"],prompts)
            sha=s.pilot.fingerprint(body)
            if sha in old_cache:
                cache=old_cache[sha]
                assert body==cache["body"]
                source="008"
                rid=cache["request_id"]
                cached[sha]=dict(body_sha256=sha,request_id=rid,receipt_path=cache["receipt_path"],receipt_sha256=cache["receipt_sha256"])
            else:
                source="009"
                rid="devjud:"+sha
                jobs[rid]=dict(request_id=rid,kind="chat",body=body)
            results[name]=dict(selection,status="ready",score_kind=config["order"],max_per_note=config["max_per_note"],candidate_ids=config["candidate_ids"],body_sha256=sha,request_id=rid,source=source)
            assignments.append(dict(proposition_id=pid,case_id=item["case_id"],method=name,status="ready",source=source,request_id=rid,body_sha256=sha))
        outputs[pid]=dict(proposition_id=pid,case_id=item["case_id"],subject_id=item["subject_id"],author_type=item["author_type"],text=item["text"],
            admission=item["admission"],scores=scored[pid],rankings=item["rankings"],retrieval=results,diagnostic=item["diagnostic"])
    repeats=[]
    for item in inputs:
        if not item["repeat_baseline"]:
            continue
        base=outputs[item["proposition_id"]]["retrieval"]["A48"]
        old_sha=previous[item["proposition_id"]]["retrieval"]["direct"]["body_sha256"]
        body=old_cache[old_sha]["body"]
        rid="devrepeat:"+item["proposition_id"]
        jobs[rid]=dict(request_id=rid,kind="chat",body=body)
        repeats.append(dict(proposition_id=item["proposition_id"],case_id=item["case_id"],request_id=rid,canonical_request_id=old_cache[old_sha]["request_id"],
            body_sha256=old_sha,source="008_vs_009_cross_day_diagnostic_only"))
        cached[old_sha]=dict(body_sha256=old_sha,request_id=old_cache[old_sha]["request_id"],receipt_path=old_cache[old_sha]["receipt_path"],receipt_sha256=old_cache[old_sha]["receipt_sha256"])
    ordered=sorted(jobs.values(),key=lambda j:s.pilot.digest_text("009/devjudge-order/v1:"+j["request_id"]))
    out=s.OUT/"development_001/judge_preparation"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"inputs.jsonl",list(outputs.values()))
    s.pilot.write_csv(out/"assignments.csv",assignments)
    s.pilot.write_json(out/"cache_bindings.json",cached)
    s.pilot.write_json(out/"repeats.json",repeats)
    s.pilot.write_json(out/"rerank_sentinels.json",sentinel)
    s.pilot.write_jsonl(out/"jobs.jsonl",ordered)
    summary=dict(logical_conditions=len(assignments),cached_logical_conditions=sum(a["source"]=="008" for a in assignments),new_requests=len(ordered),
        repeats=len(repeats),missing_evidence_conditions=sum(a["status"]!="ready" for a in assignments),
        sentinel_max_abs_difference=max(x["absolute_difference"] for x in sentinel),new_rerank_failures=failures,
        original_A_reference_identical=sum(outputs[pid]["retrieval"]["A48"].get("reference")==previous[pid]["retrieval"]["direct"]["reference"] for pid in outputs),
        expected_judge_peak_cny=sum((sum(len(m["content"]) for m in j["body"]["messages"])*.4*3+350*9)/1e6 for j in ordered))
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[prep/"manifest.json",s.OUT/"live/dev_embed/state.json",s.PRIOR/"live/judge/state.json",s.OUT/"execution_amendment_001.md"],
        [s.TASK/"build_development_judge.py",s.TASK/"io009.py",s.TASK/"study009.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    build()
