"""Independent field isolation and whole-passage checks before Judge execution."""
from pathlib import Path
import argparse
import study009 as s
from io009 import old_judge_cache


def check(folder):
    s.check(folder/"judge_preparation")
    inputs={x["proposition_id"]:x for x in s.pilot.jsonl(folder/"judge_preparation/inputs.jsonl")}
    passages={x["passage_id"]:x for x in s.pilot.jsonl(folder/"preparation/corpus.jsonl")}
    assignments=s.pilot.read_csv(folder/"judge_preparation/assignments.csv")[1]
    jobs={x["request_id"]:x for x in s.pilot.jsonl(folder/"judge_preparation/jobs.jsonl")}
    prompts=s.read_json(folder/"preparation/judge_prompts.json")
    cache=old_judge_cache() if (folder/"judge_preparation/cache_bindings.json").exists() else {}
    seen={}
    checked=0
    for a in assignments:
        if a["status"]!="ready":
            continue
        item=inputs[a["proposition_id"]]
        r=item["retrieval"][a["method"]]
        body=cache[a["body_sha256"]]["body"] if a["source"]=="008" else jobs[a["request_id"]]["body"]
        assert set(body)=={"model","messages","temperature","max_tokens","enable_thinking","n","stream","response_format"}
        assert body["model"]==s.CHAT_MODEL and body["temperature"]==0 and body["max_tokens"]==2048 and body["enable_thinking"] is False
        assert body["messages"][0]["content"]==prompts["common"]+"\n"+prompts["structured"]
        assert s.pilot.strict_json(body["messages"][1]["content"])==dict(proposition=item["text"],reference=r["reference"])
        assert s.pilot.fingerprint(body)==a["body_sha256"]
        assert len(r["selected_ids"])<=16 and set(r["selected_ids"])<=set(r["candidate_ids"]) and r["body_characters"]<=8000
        assert all(passages[key]["subject_id"]==item["subject_id"] for key in r["selected_ids"])
        for n,key in enumerate(r["selected_ids"],1):
            assert s.core.display_line(n,passages[key]) in r["reference"]
        assert a["body_sha256"] not in seen or seen[a["body_sha256"]]==(a["source"],a["request_id"])
        seen[a["body_sha256"]]=(a["source"],a["request_id"])
        checked+=1
    result=dict(ready_conditions=checked,unique_canonical_bodies=len(seen),original_claim_and_ehr_only=True,whole_passages=True,independent_ceiling=True,body_cache_consistent=True,api_calls=0)
    target=folder/"readiness_001.json"
    s.pilot.write_json(target,result)
    print(s.pilot.canonical(result))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    check(p.parse_args().folder)
