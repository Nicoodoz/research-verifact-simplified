"""085A offline selfcheck; never reads evaluation GT or reaches AWS runtime."""
from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

from parse_r1 import ParserProfile, parse
from sagemaker_provider import AwsTarget, SageMakerTransport, offline_configuration, endpoint_summary, identity_summary
from deferred_preflight085 import cases_for_stage

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/085_r1_70b_model_swap"
TASK=ROOT/"tasks/085_r1_70b_model_swap"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding="utf-8-sig"))
def lines(path): return [json.loads(s) for s in Path(path).read_text(encoding="utf-8-sig").splitlines() if s]


class FakeClient:
    def __init__(self,service,calls): self.service=service; self.calls=calls
    def get_caller_identity(self):
        self.calls.append("sts")
        return {"Account":"123456789012","Arn":"arn:aws:sts::123456789012:assumed-role/mock/test"}
    def describe_endpoint(self,**kw):
        self.calls.append("describe")
        return {"EndpointName":kw["EndpointName"],"EndpointStatus":"InService","ProductionVariants":[]}
    def invoke_endpoint(self,**kw):
        self.calls.append("invoke")
        return {"Body":None}
    def invoke_endpoint_with_response_stream(self,**kw):
        self.calls.append("stream")
        return {"Body":None}


class FakeSession:
    def __init__(self): self.calls=[]
    def client(self,name): return FakeClient(name,self.calls)


def main():
    checks=[]
    def ok(condition,name):
        if not condition: raise AssertionError(name)
        checks.append(name)
    source=read(OUT/"source_manifest.json")
    for rel,expected in source["source_sha256"].items(): ok(sha(ROOT/rel)==expected,"source_sha:"+rel)
    ok(source["evaluation_GT_read"] is False and source["new_inference_calls"]==0,"no_GT_no_inference")
    frozen=read(ROOT/"outputs/084_f4_coverage_validation/freeze.json")
    ok(sha(ROOT/"outputs/084_f4_coverage_validation/sample_blind.jsonl")==frozen["sample_sha256"],"084_sample_freeze")
    ok(sha(ROOT/"outputs/084_f4_coverage_validation/main_jobs.jsonl")==frozen["jobs_sha256"],"084_jobs_freeze")
    manifest=lines(OUT/"frozen_cohort_manifest.jsonl")
    jobs=lines(OUT/"neutral_jobs.jsonl")
    ok(len(manifest)==180 and len({x["id"] for x in manifest})==180 and len({x["sid"] for x in manifest})==21,"cohort_180_21")
    ok(len(jobs)==360 and Counter(x["arm"] for x in jobs)=={"B":180,"F4":180},"neutral_360")
    m={x["id"]:x for x in manifest}
    sem=read(OUT/"prompt_semantics.json")
    ok(len(sem["F4_demonstrations_in_order"])==4,"four_demos")
    training=lines(ROOT/"outputs/071_judge_icl_feasibility/examples.jsonl")
    ok({x["sid"] for x in training}.isdisjoint({x["sid"] for x in manifest}),"four_example_patients_disjoint")
    for j in jobs:
        ok(j["sid"]==m[j["id"]]["sid"],"sid:"+j["id"]+j["arm"])
        ok(hashlib.sha256(j["claim"].encode()).hexdigest()==m[j["id"]]["claim_sha256"],"claim:"+j["id"]+j["arm"])
        ok(hashlib.sha256(j["reference"].encode()).hexdigest()==m[j["id"]]["reference_sha256"],"reference:"+j["id"]+j["arm"])
        ok(j["instruction_semantic_content"]==sem[f'{j["arm"]}_system_content'],"prompt:"+j["id"]+j["arm"])
        ok(j["demonstrations_in_order"]==([] if j["arm"]=="B" else sem["F4_demonstrations_in_order"]),"demos:"+j["id"]+j["arm"])
        ok(not any(k in j for k in ("human_gt","GT","enable_thinking","reasoning_effort","response_format")),"neutral_keys:"+j["id"]+j["arm"])
    lengths=lines(OUT/"tokenizer_lengths.jsonl")
    audit=read(OUT/"tokenizer_length_audit.json")
    selected=read(OUT/"preflight_selection.json")
    ok(len(lengths)==360 and sha(OUT/"tokenizer_lengths.jsonl")==selected["lengths_sha256"],"token_lengths_freeze")
    ok(sha(OUT/"neutral_jobs.jsonl")==selected["source_neutral_sha256"],"selection_input_freeze")
    ok(len(cases_for_stage("B"))==3 and len({j["id"] for _,j in cases_for_stage("B")})==3,"preflight_three_distinct")
    ok([name for name,_ in cases_for_stage("B")]==["short_B","median_F4","longest_F4"],"preflight_roles")
    token=read(OUT/"tokenizer_source.json")
    allowed={"config.json","generation_config.json","tokenizer.json","tokenizer_config.json"}
    ok(set(token["files"])==allowed,"tokenizer_allowlist")
    ok(all((ROOT/".local_models/085a_r1_tokenizer"/name).is_file() and
           sha(ROOT/".local_models/085a_r1_tokenizer"/name)==v["sha256"]
           for name,v in token["files"].items()),"tokenizer_hashes")
    ok(not any(x.suffix in (".safetensors",".bin",".pt") for x in (ROOT/".local_models/085a_r1_tokenizer").rglob("*")),"no_model_weights")
    ok(audit["status"]=="OFFLINE_TOKENIZER_AUDIT_NO_ENDPOINT" and audit["provider_context_verified"] is False,"audit_status")
    profile=ParserProfile(content_path=["output"],finish_path=["finish"])
    good=json.dumps({"output":"<think>private reasoning</think>prefix {\"verdict\":\"Not Supported\",\"label_scores\":{\"Supported\":2,\"Not Supported\":96,\"Not Addressed\":2}} suffix","finish":"stop"})
    parsed=parse(good,profile)
    ok(parsed["valid"] and parsed["verdict"]=="Not Supported" and parsed["reasoning"]=="private reasoning" and parsed["label_scores"]["Not Supported"]==96,"parser_think_json")
    ok(not parse({"output":"reason says Supported","finish":"stop"},profile)["valid"],"parser_no_reason_guess")
    ok(not parse({"output":"{\"verdict\":\"Supported\"}","finish":"length"},profile)["valid"],"parser_truncation_invalid")
    ok(not parse({"output":"<think>unfinished {\"verdict\":\"Supported\"}","finish":"stop"},profile)["valid"],"parser_unclosed_thinking_invalid")
    fs=FakeSession(); target=AwsTarget(region="ap-northeast-1",endpoint_name="mock-endpoint")
    ok(offline_configuration(target)["inference_calls"]==0 and fs.calls==[],"offline_no_aws")
    ok(identity_summary(fs)["account_masked"].endswith("9012") and fs.calls==["sts"],"masked_identity")
    ok(endpoint_summary(fs,target)["in_service"] and fs.calls==["sts","describe"],"describe_only")
    transport=SageMakerTransport(target,session=fs)
    try: transport.invoke(payload=b"{}",content_type="application/json",accept="application/json")
    except PermissionError: pass
    else: raise AssertionError("allow_inference gate failed")
    ok(fs.calls==["sts","describe"],"invoke_gate_no_runtime")
    try: transport.invoke_stream(payload=b"{}",content_type="application/json",accept="application/json",allow_inference=True)
    except PermissionError: pass
    else: raise AssertionError("stream verification gate failed")
    ok(fs.calls==["sts","describe"],"stream_gate_no_runtime")
    diff=subprocess.check_output(["git","diff","--name-only","--",".gitignore"],cwd=ROOT,text=True).strip()
    ok(not diff,"gitignore_unchanged")
    result={"status":"PASS","checks":len(checks),"no_AWS_runtime_calls":True,"no_GT_read":True,
            "no_model_weights":True,"new_inference_cost_cny":0,"examples":checks[:12]}
    (OUT/"selfcheck.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"status":"PASS","checks":len(checks)},ensure_ascii=False))


if __name__=="__main__": main()
