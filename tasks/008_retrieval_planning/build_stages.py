"""Offline transformations of immutable 008 native receipts. No network calls."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import argparse
import json
import re
import numpy as np
import common as c
import planning_core as pc
from prepare_experiment import embedding_jobs
from services import cost


def phase_data(phase):
    base=c.OUT/"live"/phase
    manifest=c.read_json(base/"manifest.json")
    state=c.read_json(base/"state.json")
    assert state["run_id"]==c.pilot.fingerprint(manifest)
    assert not state.get("bound_violation")
    values={}
    attempts=[]
    for job in manifest["jobs"]:
        progress=state["jobs"][job["request_id"]]
        assert progress["status"]=="received", (phase,job["request_id"],progress["status"])
        terminal=[]
        for ptr in progress["receipts"]:
            path=base/ptr["file"]
            assert c.pilot.digest_file(path)==ptr["sha256"]
            receipt=c.read_json(path)
            assert receipt["run_id"]==state["run_id"] and receipt["job_sha256"]==c.pilot.fingerprint(job)
            assert receipt["request_id"]==job["request_id"]
            charge,basis=cost(job,receipt["transport"])
            assert abs(charge-ptr["charge_cny"])<1e-10 and basis==ptr["charge_basis"]
            attempts.append(dict(phase=phase,request_id=job["request_id"],file=path.relative_to(c.OUT).as_posix(),sha256=ptr["sha256"],
                attempt=receipt["attempt"],http_status=receipt["transport"]["http_status"],charge_cny=charge,charge_basis=basis,account=receipt["account"]))
            if receipt["transport"]["http_status"]==200:
                terminal.append(receipt)
        assert len(terminal)==1,"A success was regenerated or lost"
        receipt=terminal[0]
        values[job["request_id"]]=dict(job=job,receipt=receipt,native=c.pilot.strict_json(receipt["transport"]["body_text"]))
    assert abs(sum(r["charge_cny"] for r in attempts)-state["used_or_reserved_cny"])<1e-8
    assert state["used_or_reserved_cny"]<=manifest["cap_cny"]
    return values,attempts


def seal(out,dependencies,extra=None,code_files=()):
    c.pilot.write_json(out/"manifest.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),
        dependencies={p.relative_to(c.ROOT).as_posix():c.pilot.digest_file(p) for p in dependencies},
        code_sha256={p.relative_to(c.ROOT).as_posix():c.pilot.digest_file(p) for p in [Path(__file__),c.TASK/"planning_core.py",*code_files]},
        files={p.name:c.pilot.digest_file(p) for p in out.iterdir() if p.is_file()},details=extra or {}))


def plans():
    c.check_files(c.OUT/"preparation_001")
    values,_=phase_data("planner")
    base=c.OUT/"preparation_001"
    catalog=c.read_json(base/"embedding_catalog.json")
    outputs=[]
    extras={}
    for item in c.pilot.jsonl(base/"inputs.jsonl"):
        native=values["plan:"+item["proposition_id"]]["native"]
        choice=native.get("choices",[{}])[0]
        text=choice.get("message",{}).get("content")
        try:
            c.pilot.require(native.get("model")==c.CHAT_MODEL and len(native["choices"])==1,"Planner model/choice mismatch")
            c.pilot.require(choice["finish_reason"]=="stop","Planner incomplete generation")
            usage=c.sf.normalize_usage(native)
            c.pilot.require(usage["reasoning_tokens"]==0 and not choice["message"].get("reasoning_content"),"Planner thinking mismatch")
            plan=pc.parse_plan(text,item)
            error=None
        except (ValueError,TypeError,KeyError,IndexError) as e:
            plan=dict(queries=[])
            error=str(e)
        queries=[q for q in plan["queries"] if q!=item["text"]]
        for q in queries:
            hid=c.pilot.digest_text(q)
            if hid not in catalog:
                extras[hid]=q
        claim_numbers=set(re.findall(r"\d+(?:\.\d+)?",item["text"]))
        query_numbers=set(re.findall(r"\d+(?:\.\d+)?"," ".join(queries)))
        outputs.append(dict(proposition_id=item["proposition_id"],case_id=item["case_id"],status="fallback_direct" if error else "valid_schema",
            error=error,output_text=text,finish_reason=choice.get("finish_reason"),plan=plan,queries=queries,
            query_numbers_not_in_claim=sorted(query_numbers-claim_numbers),semantic_validity_not_established=True))
    out=c.OUT/"plans_001"
    out.mkdir(parents=True,exist_ok=False)
    c.pilot.write_jsonl(out/"plans.jsonl",outputs)
    c.pilot.write_json(out/"embedding_catalog.json",extras)
    c.pilot.write_jsonl(out/"embedding_jobs.jsonl",embedding_jobs(extras,"plans"))
    summary=dict(claims=len(outputs),status_counts=dict(Counter(x["status"] for x in outputs)),
        query_counts=dict(Counter(len(x["queries"]) for x in outputs)),new_embedding_texts=len(extras),
        new_embedding_requests=len(embedding_jobs(extras,"plans")),number_expansion_flags=sum(bool(x["query_numbers_not_in_claim"]) for x in outputs))
    c.pilot.write_json(out/"summary.json",summary)
    seal(out,[base/"manifest.json",c.OUT/"live/planner/manifest.json",c.OUT/"live/planner/state.json"])
    print(c.pilot.canonical(summary))


def embedding_vectors():
    vectors={}
    for phase in ("embedding_base","embedding_plans"):
        if phase=="embedding_plans" and not c.pilot.jsonl(c.OUT/"plans_001/embedding_jobs.jsonl"):
            continue
        values,_=phase_data(phase)
        for value in values.values():
            job,native=value["job"],value["native"]
            assert native.get("model")==c.EMBED_MODEL,"Embedding alias changed"
            data=native["data"]
            assert len(data)==len(job["text_ids"])
            assert sorted(x["index"] for x in data)==list(range(len(data)))
            for x in data:
                key=job["text_ids"][x["index"]]
                vector=np.asarray(x["embedding"],dtype=np.float64)
                assert vector.shape==(1024,) and np.isfinite(vector).all() and np.linalg.norm(vector)>0
                assert key not in vectors
                vectors[key]=vector
    return vectors


def candidates():
    c.check_files(c.OUT/"preparation_001")
    c.check_files(c.OUT/"plans_001")
    base=c.OUT/"preparation_001"
    vectors=embedding_vectors()
    corpus=c.pilot.jsonl(base/"corpus.jsonl")
    passage={x["passage_id"]:x for x in corpus}
    indices={sid:pc.HybridIndex([x for x in corpus if x["subject_id"]==sid],
        [vectors[x["embedding_id"]] for x in corpus if x["subject_id"]==sid]) for sid in c.PATIENTS}
    plans_by_id={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"plans_001/plans.jsonl")}
    outputs,jobs=[],[]
    for item in c.pilot.jsonl(base/"inputs.jsonl"):
        pid=item["proposition_id"]
        queries=dict(direct=[item["text"]],simple=list(dict.fromkeys([item["text"],item["source"]["sentence"],item["source"]["local"]])),
            planner=list(dict.fromkeys([item["text"]]+plans_by_id[pid]["queries"])))
        ranks={q:indices[item["subject_id"]].retrieve(q,vectors[c.pilot.digest_text(q)]) for q in dict.fromkeys(q for qs in queries.values() for q in qs)}
        pools={arm:pc.candidate_pool([ranks[q]["hybrid"] for q in qs]) for arm,qs in queries.items()}
        union=sorted(set(x for pool in pools.values() for x in pool))
        texts=[passage[key]["search_text"] for key in union]
        assert all(len((item["text"]+t).encode("utf-8"))<8192 for t in texts)
        jobs.append(dict(request_id="rerank:"+pid,kind="rerank",body=dict(model=c.RERANK_MODEL,query=item["text"],documents=texts,
            top_n=len(union),return_documents=False,max_chunks_per_doc=1),passage_ids=union))
        outputs.append(dict(proposition_id=pid,case_id=item["case_id"],subject_id=item["subject_id"],queries=queries,
            query_rankings=[dict(query=q,**r) for q,r in ranks.items()],candidate_ids=pools,union_ids=union))
    jobs.sort(key=lambda j:c.pilot.digest_text("008/rerank-order/v1:"+j["request_id"]))
    out=c.OUT/"candidates_001"
    out.mkdir(parents=True,exist_ok=False)
    c.pilot.write_jsonl(out/"candidates.jsonl",outputs)
    c.pilot.write_jsonl(out/"rerank_jobs.jsonl",jobs)
    keys=sorted(vectors)
    np.save(out/"embedding_vectors.npy",np.asarray([vectors[key] for key in keys]),allow_pickle=False)
    c.pilot.write_json(out/"embedding_ids.json",keys)
    summary=dict(claims=len(outputs),vectors=len(vectors),dimension=1024,rerank_requests=len(jobs),
        mean_union=sum(len(x["union_ids"]) for x in outputs)/len(outputs),max_union=max(len(x["union_ids"]) for x in outputs),
        mean_candidate_counts={a:sum(len(x["candidate_ids"][a]) for x in outputs)/len(outputs) for a in c.METHODS})
    c.pilot.write_json(out/"summary.json",summary)
    dep=[base/"manifest.json",c.OUT/"plans_001/manifest.json",c.OUT/"live/embedding_base/state.json"]
    if (c.OUT/"live/embedding_plans/state.json").exists():
        dep.append(c.OUT/"live/embedding_plans/state.json")
    seal(out,dep)
    print(c.pilot.canonical(summary))


def judge_body(item,reference,prompts):
    return dict(model=c.CHAT_MODEL,messages=[dict(role="system",content=prompts["common"]+"\n"+prompts["structured"]),
        dict(role="user",content=c.pilot.canonical(dict(proposition=item["text"],reference=reference)))],
        temperature=0,max_tokens=2048,enable_thinking=False,n=1,stream=False,response_format=c.sf.response_schema())


def judge():
    c.check_files(c.OUT/"preparation_001")
    c.check_files(c.OUT/"candidates_001")
    values,_=phase_data("rerank")
    base=c.OUT/"preparation_001"
    inputs=c.pilot.jsonl(base/"inputs.jsonl")
    candidate={x["proposition_id"]:x for x in c.pilot.jsonl(c.OUT/"candidates_001/candidates.jsonl")}
    passage={x["passage_id"]:x for x in c.pilot.jsonl(base/"corpus.jsonl")}
    prompts=c.read_json(base/"judge_prompts.json")
    unique,outputs,assignments,jobs={},{},[],[]
    for item in inputs:
        pid=item["proposition_id"]
        value=values["rerank:"+pid]
        # Some rerank APIs omit model; retain that absence, never substitute a weights version.
        if value["native"].get("model") is not None:
            assert value["native"]["model"]==c.RERANK_MODEL
        results=value["native"]["results"]
        union=candidate[pid]["union_ids"]
        assert value["job"]["passage_ids"]==union and len(results)==len(union)
        assert sorted(x["index"] for x in results)==list(range(len(union)))
        scores={union[x["index"]]:float(x["relevance_score"]) for x in results}
        assert all(np.isfinite(v) for v in scores.values())
        arms={}
        for arm in c.METHODS:
            selected=pc.select_evidence(candidate[pid]["candidate_ids"][arm],scores,passage,item["admission"])
            body=judge_body(item,selected["reference"],prompts)
            sha=c.pilot.fingerprint(body)
            if sha not in unique:
                rid="judge:"+sha
                unique[sha]=rid
                jobs.append(dict(request_id=rid,kind="chat",body=body))
            assignments.append(dict(proposition_id=pid,case_id=item["case_id"],method=arm,request_id=unique[sha],body_sha256=sha))
            arms[arm]=dict(selected,body_sha256=sha,request_id=unique[sha])
        outputs[pid]=dict(proposition_id=pid,case_id=item["case_id"],subject_id=item["subject_id"],author_type=item["author_type"],
            text=item["text"],scores=scores,retrieval=arms)
    repeated=[]
    for sid in c.PATIENTS:
        for author in ("llm","human"):
            item=min([x for x in inputs if x["subject_id"]==sid and x["author_type"]==author],key=lambda x:c.pilot.digest_text("008/repeat/v1:"+x["proposition_id"]))
            pid=item["proposition_id"]
            body=judge_body(item,outputs[pid]["retrieval"]["direct"]["reference"],prompts)
            rid="repeat:"+pid
            jobs.append(dict(request_id=rid,kind="chat",body=body))
            repeated.append(dict(proposition_id=pid,case_id=item["case_id"],subject_id=sid,author_type=author,request_id=rid,
                canonical_request_id=outputs[pid]["retrieval"]["direct"]["request_id"],body_sha256=c.pilot.fingerprint(body)))
    jobs.sort(key=lambda j:c.pilot.digest_text("008/judge-order/v1:"+j["request_id"]))
    out=c.OUT/"judge_preparation_001"
    out.mkdir(parents=True,exist_ok=False)
    c.pilot.write_jsonl(out/"inputs.jsonl",list(outputs.values()))
    c.pilot.write_jsonl(out/"jobs.jsonl",jobs)
    c.pilot.write_csv(out/"assignments.csv",assignments)
    c.pilot.write_json(out/"repeat_assignments.json",repeated)
    summary=dict(logical_judgments=len(assignments),canonical_requests=len(unique),repeat_requests=len(repeated),actual_requests=len(jobs),
        saved_requests=len(assignments)-len(unique),equal_direct_references={a:sum(x["retrieval"][a]["body_sha256"]==x["retrieval"]["direct"]["body_sha256"] for x in outputs.values()) for a in c.METHODS},
        mean_reference_characters={a:sum(len(x["retrieval"][a]["reference"]) for x in outputs.values())/len(inputs) for a in c.METHODS},
        maximum_body_characters={a:max(x["retrieval"][a]["body_characters"] for x in outputs.values()) for a in c.METHODS},
        empty_evidence_counts={a:sum(not x["retrieval"][a]["selected_ids"] for x in outputs.values()) for a in c.METHODS},source_sent_to_judge=False)
    c.pilot.write_json(out/"summary.json",summary)
    seal(out,[base/"manifest.json",c.OUT/"candidates_001/manifest.json",c.OUT/"live/rerank/state.json"],dict(shared_selector="original_claim_cross_encoder"))
    print(c.pilot.canonical(summary))


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("stage",choices=["plans","candidates","judge"])
    args=ap.parse_args()
    globals()[args.stage]()
