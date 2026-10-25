"""Offline reproducibility and safety checks before asking for a paid-run budget."""
import csv
import gzip
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import context_feasibility as cf
import run_context_pilot as execution


def main():
    prep=cf.OUT/"preparation_001"
    out=cf.fresh("verification_offline")
    code=("import sys,unittest\nfrom unittest.mock import patch\n"
        "with patch('socket.socket.connect',side_effect=AssertionError('Network disabled')), "
        "patch('socket.socket.connect_ex',side_effect=AssertionError('Network disabled')), "
        "patch('socket.create_connection',side_effect=AssertionError('Network disabled')):\n"
        "    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))\n"
        "sys.exit(not result.wasSuccessful())\n")
    tests=subprocess.run([sys.executable,"-B","-c",code],cwd=cf.ROOT,capture_output=True,text=True,encoding="utf-8")
    (out/"tests.log").write_text(tests.stdout+tests.stderr,encoding="utf-8",newline="\n")
    cf.pilot.require(tests.returncode==0,"Offline tests failed")
    with patch("socket.socket.connect",side_effect=AssertionError("Network disabled")),patch("socket.socket.connect_ex",side_effect=AssertionError("Network disabled")),patch("socket.create_connection",side_effect=AssertionError("Network disabled")):
        jobs=execution.load_preparation(prep)
        repeated=cf.prepare()
    manifest=json.loads((prep/"manifest.json").read_text(encoding="utf-8"))
    same={name:cf.pilot.digest_file(prep/name)==cf.pilot.digest_file(repeated/name) for name in manifest["output_sha256"]}
    cf.pilot.require(all(same.values()),"Preparation changed on repeat")
    inputs={x["proposition_id"]:x for x in cf.pilot.jsonl(prep/"inputs.jsonl")}
    for pid,item in inputs.items():
        own=[j for j in jobs if j["request_id"].endswith(":"+pid)]
        cf.pilot.require(len(own)==3,"Incomplete arms")
        controls=[{k:v for k,v in j["body"].items() if k!="messages"} for j in own]
        cf.pilot.require(controls[0]==controls[1]==controls[2],"Unequal native settings")
        for j in own:
            data=json.loads(j["body"]["messages"][1]["content"])
            cf.pilot.require(set(data)=={"proposition","reference","unverified_source_text"},"Unexpected model data field")
            cf.pilot.require(data["proposition"]==item["text"] and data["reference"]==item["reference"],"Claim or EHR changed between arms")
    props=cf.pilot.subset_csv(cf.RAW/"propositions/propositions.csv.gz","proposition_id",set(inputs))
    for row in props:
        item=inputs[row["proposition_id"]]
        cf.pilot.require(cf.source_window(row)==item["source_context"],"Source offsets or context changed")
    verdict=[j for j in jobs if "human_gt" in json.loads(j["body"]["messages"][1]["content"])]
    cf.pilot.require(not verdict,"GT leaked into model fields")
    forbidden=subprocess.run(["git","diff","--name-only","--","tasks/001_dataset_audit","tasks/002_reproduce_paper_results", "tasks/003_error_analysis","tasks/004_event_alignment_pilot","tasks/005_pilot_effect_analysis",
        "outputs/001_dataset_audit","outputs/002_reproduce_paper_results","outputs/003_error_analysis","outputs/004_event_alignment_pilot","outputs/005_pilot_effect_analysis","reviews","environment.yml",".gitignore","src/verifact_research/evaluation","src/verifact_research/inference"],cwd=cf.ROOT,capture_output=True,text=True,check=True)
    cf.pilot.require(not forbidden.stdout.strip(),"Existing frozen work changed")
    version_files=[*cf.TASK.glob("*.py"),cf.ROOT/"tests/test_source_context_feasibility.py"]
    result=dict(stage="offline_preparation_verified_waiting_budget_approval",tests_run=int(re.search(r"Ran (\d+) tests",tests.stderr).group(1)),
        tests_exit_code=0,new_test_count=9,network_blocked_for_tests_and_preparation=True,new_inference_calls=0,
        selected_claims=len(inputs),native_requests=len(jobs),same_claim_and_reference=True,same_generation_settings=True,
        source_context_offsets_verified=len(props),gt_fields_not_sent=True,existing_tasks_and_evaluation_unchanged=True,
        repeated_preparation=repeated.relative_to(cf.ROOT).as_posix(),repeated_files_byte_identical=same,
        preparation_manifest_sha256=cf.pilot.digest_file(prep/"manifest.json"),
        code_sha256={p.relative_to(cf.ROOT).as_posix():cf.pilot.digest_file(p) for p in version_files},
        independent_audit_performed=False,real_service_test_performed=False)
    cf.pilot.write_json(out/"verification.json",result)
    print(cf.pilot.canonical(dict(verification=str(out),tests=result["tests_run"],identical_files=len(same))))


if __name__=="__main__":
    main()
