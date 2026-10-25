"""Deferred SageMaker preflight. No runtime request without --allow-inference.

Payload builder contract (deployment-specific, supplied after sample inference code):
  build_payload(neutral_job: dict, settings: dict) -> (body_bytes, content_type, accept)
This module has no default implementation and never guesses a JumpStart schema.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import time
from pathlib import Path

from sagemaker_provider import AwsTarget, SageMakerTransport, diagnose
from parse_r1 import ParserProfile, parse

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/085_r1_70b_model_swap"
RUN = OUT / "deferred_preflight"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_lines(path: Path):
    return [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def write_once(path: Path, content: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as f:
        f.write(content)


def builder_from_file(path: Path):
    spec = importlib.util.spec_from_file_location("deployment_payload_plugin_085", path)
    if spec is None or spec.loader is None:
        raise ValueError("Invalid payload plugin")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "build_payload", None)):
        raise ValueError("Plugin must define build_payload(job, settings)")
    return module.build_payload


def make_a_job():
    semantics = read_json(OUT / "prompt_semantics.json")
    return {"id": "FICTIONAL-A-NO-PATIENT", "sid": "FICTIONAL", "arm": "B",
        "claim": "The fictional patient received a blue scarf.",
        "reference": "[1] Fictional record: the patient received a blue scarf.",
        "instruction_semantic_content": semantics["B_system_content"],
        "demonstrations_in_order": [], "expected_output_schema": semantics["expected_output_schema"]}


def cases_for_stage(stage: str):
    if stage == "A":
        return [("A_fictional", make_a_job())]
    selected = read_json(OUT / "preflight_selection.json")
    assert selected["status"] == "FROZEN_BEFORE_ENDPOINT_AND_R1_GT"
    assert hashlib.sha256((OUT / "neutral_jobs.jsonl").read_bytes()).hexdigest() == selected["source_neutral_sha256"]
    jobs = {(j["id"], j["arm"]): j for j in read_lines(OUT / "neutral_jobs.jsonl")}
    return [(case["role"], jobs[case["id"], case["arm"]]) for case in selected["cases"]]


def invoke_stage(stage: str, args):
    if not args.allow_inference:
        print(json.dumps({"stage":stage,"planned": [name for name, _ in cases_for_stage(stage)],
                          "inference_calls":0,"gate":"--allow-inference absent"},ensure_ascii=False))
        return
    target = AwsTarget.from_env(region=args.region, profile=args.profile,
        endpoint_name=args.endpoint_name, inference_component_name=args.inference_component_name)
    if not args.payload_plugin or not target.endpoint_name:
        raise ValueError("Deployment-specific --payload-plugin and configured endpoint name are required")
    if stage == "B":
        if not (RUN / "A_fictional.raw").exists():
            raise RuntimeError("Stage A raw response required before research preflight")
        if args.actual_context is None or args.output_reserve is None:
            raise ValueError("B requires confirmed --actual-context and --output-reserve")
        lengths = {(x["id"],x["arm"]):x["chat_input_tokens"]
                   for x in read_lines(OUT / "tokenizer_lengths.jsonl")}
        for _, job in cases_for_stage("B"):
            needed = lengths[job["id"],job["arm"]] + args.output_reserve
            if needed > args.actual_context:
                raise RuntimeError(f"Context insufficient for {job['id']} {job['arm']}: {needed}>{args.actual_context}; no request sent")
    builder = builder_from_file(args.payload_plugin)
    diagnostic = diagnose(target)  # only STS and Describe; no runtime
    if not diagnostic["endpoint"]["in_service"]:
        raise RuntimeError("Endpoint is not InService")
    transport = SageMakerTransport(target)
    settings = {"max_new_tokens": args.output_reserve, "actual_context": args.actual_context,
                "sample_code_reviewed": True}
    for name, job in cases_for_stage(stage):
        raw_path = RUN / f"{name}.raw"
        meta_path = RUN / f"{name}.json"
        if raw_path.exists() or meta_path.exists():
            raise FileExistsError(f"Preflight {name} already attempted; never resend a successful answer")
        body, content_type, accept = builder(job, settings)
        if not isinstance(body, bytes):
            raise TypeError("Plugin body must be bytes")
        t0=time.monotonic()
        try:
            response = transport.invoke(payload=body,content_type=content_type,accept=accept,allow_inference=True)
            raw=response["Body"].read()
        except Exception as exc:
            # Preserve unknown billability; a timeout may have reached the container.
            write_once(meta_path,json.dumps({"stage":stage,"role":name,"id":job["id"],
                "arm":job["arm"],"payload_sha256":hashlib.sha256(body).hexdigest(),
                "status":"UNKNOWN_OR_FAILED","billability":"UNKNOWN_RESERVE_REQUIRED",
                "exception_type":type(exc).__name__},sort_keys=True).encode("utf-8"))
            raise
        elapsed=time.monotonic()-t0
        # Preserve exact endpoint bytes before any parsing. No raw content printed.
        write_once(raw_path,raw)
        write_once(meta_path,json.dumps({"stage":stage,"role":name,"id":job["id"],"sid":job["sid"],
            "arm":job["arm"],"raw_sha256":hashlib.sha256(raw).hexdigest(),
            "payload_sha256":hashlib.sha256(body).hexdigest(),"elapsed_seconds":elapsed,
            "http_status":response.get("ResponseMetadata",{}).get("HTTPStatusCode"),
            "endpoint_name":target.endpoint_name,"region":target.region,
            "inference_component_name":target.inference_component_name,
            "model_id_expected":"deepseek-llm-r1-distill-llama-70b"},
            ensure_ascii=False,sort_keys=True).encode("utf-8"))
        print(json.dumps({"role":name,"saved_raw":str(raw_path),"elapsed_seconds":round(elapsed,2)},ensure_ascii=False))


def freeze_parser(args):
    """Only response structure from A/B may set envelope paths; no labels read."""
    if not args.profile_candidate:
        raise ValueError("--profile-candidate is required")
    candidate=read_json(args.profile_candidate)
    if candidate.get("status") != "CANDIDATE_FROM_AB_NO_GT":
        raise ValueError("Candidate must declare GT-blind A/B provenance")
    paths={k:candidate.get(k) for k in ("content_path","finish_path","usage_path","reasoning_path")}
    if not isinstance(paths["content_path"],list):
        raise ValueError("content_path must be an explicit path")
    results={}
    for name in ("A_fictional","short_B","median_F4","longest_F4"):
        raw_path=RUN / f"{name}.raw"
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing preflight raw: {name}")
        # For diagnosis only: invalid core may be retained, never guessed from reason.
        profile=ParserProfile(content_path=paths["content_path"],finish_path=paths["finish_path"],
                              usage_path=paths["usage_path"],reasoning_path=paths["reasoning_path"])
        results[name]=parse(raw_path.read_bytes(),profile)
    if any(not v["valid"] or v["truncated"] is not False for v in results.values()):
        raise RuntimeError("A/B must all have parseable final verdicts and explicit non-truncated finish before parser freeze")
    frozen={"status":"FROZEN_AFTER_AB_NO_GT","source":"A fictional and three frozen B preflight raw responses",
            **paths,"truncation_values":["length","max_tokens","max_new_tokens","truncated"],
            "preflight_raw_sha256":{name:hashlib.sha256((RUN/f"{name}.raw").read_bytes()).hexdigest() for name in results},
            "preflight_parse_summary":{name:{"valid":v["valid"],"invalid_reason":v["invalid_reason"],
                "truncated":v["truncated"]} for name,v in results.items()},"GT_read":False}
    write_once(RUN/"parser_profile_frozen.json",json.dumps(frozen,ensure_ascii=False,sort_keys=True).encode("utf-8"))
    print(json.dumps(frozen["preflight_parse_summary"],ensure_ascii=False))


def main():
    p=argparse.ArgumentParser(description="085 deferred A/B/C; 085A never runs this with --allow-inference")
    p.add_argument("stage",choices=("A","B","C"))
    p.add_argument("--allow-inference",action="store_true")
    p.add_argument("--payload-plugin",type=Path)
    p.add_argument("--profile-candidate",type=Path)
    p.add_argument("--endpoint-name")
    p.add_argument("--region")
    p.add_argument("--profile")
    p.add_argument("--inference-component-name")
    p.add_argument("--actual-context",type=int)
    p.add_argument("--output-reserve",type=int)
    args=p.parse_args()
    if args.stage == "C":
        freeze_parser(args)
    else:
        invoke_stage(args.stage,args)


if __name__=="__main__":
    main()
