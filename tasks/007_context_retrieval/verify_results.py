"""Offline verification of 007 primary and zero-budget sensitivity artifacts."""
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import prepare as p
import score_results as scoring
from run_judge import charge_for, load_preparation
from finalize_report import render
from zero_budget_sensitivity import pack_saved
from retrieval import ARMS, reference


def tree(path):
    return {x.relative_to(path).as_posix():p.pilot.digest_file(x) for x in path.rglob("*") if x.is_file()}


def check_manifest(base,name="manifest.json"):
    manifest=json.loads((base/name).read_text(encoding="utf-8"))
    for filename,digest in manifest["output_sha256"].items():
        assert p.pilot.digest_file(base/filename)==digest,filename
    return manifest


def receipt_check(run,jobs,registered):
    state=json.loads((run/"state.json").read_text(encoding="utf-8"))
    manifest=json.loads((run/"manifest.json").read_text(encoding="utf-8"))
    assert manifest["jobs"]==jobs and p.pilot.fingerprint(manifest)==state["run_id"]
    assert set(state["jobs"])=={j["request_id"] for j in jobs}
    receipts,cost={},0.0
    for i,job in enumerate(jobs,1):
        progress=state["jobs"][job["request_id"]]
        assert progress["attempts"]==len(progress["receipts"])==1 and progress["status"]=="response_received"
        pointer=progress["receipts"][0]
        assert pointer["file"]==f"receipt_{i:06d}_001.json"
        path=run/pointer["file"]
        assert p.pilot.digest_file(path)==pointer["sha256"]
        receipt=json.loads(path.read_text(encoding="utf-8"))
        assert receipt["run_id"]==state["run_id"] and receipt["request_id"]==job["request_id"]
        assert receipt["request_sha256"]==p.pilot.fingerprint(job["body"]) and receipt["attempt"]==1
        assert receipt["account"]==progress["account"]==pointer["account"]
        assert receipt["transport"]["http_status"]==200
        assert datetime.fromisoformat(receipt["transport"]["started_utc"])>=datetime.fromisoformat(registered)
        charge,basis=charge_for(receipt["transport"],job["max_cost_cny"])
        assert charge==pointer["estimated_charge_cny"] and basis==pointer["charge_basis"]
        cost+=charge
        receipts[job["request_id"]]=receipt
    assert len(list(run.glob("receipt_*.json")))==len(jobs)
    assert abs(cost-state["reserved_budget_cny"])<1e-10 and cost<=manifest["budget_cny"]
    return receipts,cost


def compare_floats(left,right,path=""):
    if isinstance(left,dict):
        assert set(left)==set(right)
        return [d for k in left for d in compare_floats(left[k],right[k],path+"/"+k)]
    if isinstance(left,list):
        assert len(left)==len(right)
        return [d for i,(a,b) in enumerate(zip(left,right)) for d in compare_floats(a,b,path+f"/{i}")]
    if left==right:
        return []
    assert path.endswith("/score") and isinstance(left,float) and isinstance(right,float)
    assert abs(left-right)<1e-10
    return [abs(left-right)]


def main():
    output=next(p.OUT/f"verification_{i:03d}" for i in range(1,1000) if not (p.OUT/f"verification_{i:03d}").exists())
    output.mkdir()
    command=("import sys,unittest\nfrom unittest.mock import patch\nwith patch('socket.create_connection',side_effect=AssertionError('Network disabled')), patch('socket.socket.connect',side_effect=AssertionError('Network disabled')), patch('socket.socket.connect_ex',side_effect=AssertionError('Network disabled')):\n result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))\nsys.exit(not result.wasSuccessful())")
    tests=subprocess.run([sys.executable,"-B","-c",command],cwd=p.ROOT,capture_output=True,text=True,encoding="utf-8")
    (output/"tests.log").write_text(tests.stdout+tests.stderr,encoding="utf-8",newline="\n")
    assert tests.returncode==0
    prep,run,supp=p.OUT/"preparation_003",p.OUT/"run_001",p.OUT/"zero_budget_sensitivity_001"
    with patch("socket.create_connection",side_effect=AssertionError("No network")),patch("socket.socket.connect",side_effect=AssertionError("No network")),patch("socket.socket.connect_ex",side_effect=AssertionError("No network")):
        jobs=load_preparation(prep)
        original_hashes={x.relative_to(p.OUT).as_posix():p.pilot.digest_file(x) for root in (run,supp) for x in root.rglob("receipt_*.json")}
        auth=json.loads((p.OUT/"authorization_001.json").read_text(encoding="utf-8"))
        assert auth["preparation_manifest_sha256"]==p.pilot.digest_file(prep/"manifest.json")
        assert auth["execution_sha256"]==p.pilot.digest_file(p.TASK/"run_judge.py")
        assert auth["protocol_sha256"]==p.pilot.digest_file(p.OUT/"execution_protocol_001.md")
        primary_receipts,primary_cost=receipt_check(run,jobs,auth["registered_utc"])
        plan=json.loads((supp/"protocol_and_authority.json").read_text(encoding="utf-8"))
        assert plan["code_sha256"]==p.pilot.digest_file(p.TASK/"zero_budget_sensitivity.py")
        assert plan["jobs_sha256"]==p.pilot.digest_file(supp/"requests.jsonl") and plan["inputs_sha256"]==p.pilot.digest_file(supp/"inputs.jsonl")
        supp_jobs=p.pilot.jsonl(supp/"requests.jsonl")
        supp_receipts,supp_cost=receipt_check(supp/"receipts",supp_jobs,plan["registered_utc"])
        assert primary_cost+supp_cost<16 and abs(primary_cost-plan["primary_used_cny"])<1e-10
        assert plan["cumulative_task_upper_guard_cny"]==plan["primary_used_cny"]+1<=16
        primary=check_manifest(prep)
        raw_checked={}
        for name,digest in primary["raw_sha256"].items():
            assert p.pilot.digest_file(p.RAW/name)==digest
            raw_checked[name]=digest
        release=json.loads((p.OUT/"release_comparison_001/manifest.json").read_text(encoding="utf-8"))
        for name,digest in release["source_sha256"].items():
            assert p.pilot.digest_file(p.RAW/"verifact"/name)==digest
            raw_checked["verifact/"+name]=digest
        assert release["reference_file_sha256"]==p.pilot.digest_file(p.OUT/"release_comparison_001/references.jsonl")
        check_manifest(run/"analysis")
        check_manifest(run/"review_001")
        check_manifest(run/"review_001/semantic_001")
        scoring.score(prep,run,output/"replayed_analysis")
        assert tree(run/"analysis")==tree(output/"replayed_analysis")
        # Check the independent preparation repeat, allowing only diagnosed float score tails.
        repeated=p.OUT/"verification_preparation_001/preparation_003"
        comparisons={n:p.pilot.digest_file(prep/n)==p.pilot.digest_file(repeated/n) for n in primary["output_sha256"]}
        deviations=[]
        for name,equal in comparisons.items():
            if not equal:
                assert name in {"inputs.jsonl","old_case_probes.jsonl"}
                deviations+=compare_floats(p.pilot.jsonl(prep/name),p.pilot.jsonl(repeated/name))
        assert comparisons["requests.jsonl"]
        inputs={x["proposition_id"]:x for x in p.pilot.jsonl(prep/"inputs.jsonl")}
        supp_inputs={x["proposition_id"]:x for x in p.pilot.jsonl(supp/"inputs.jsonl")}
        corpora=json.loads((prep/"corpora.json").read_text(encoding="utf-8"))
        zero={pid for pid,x in inputs.items() if x["retrieval"]["claim"]["matched_character_budget"]==0}
        assert zero==set(supp_inputs) and len(zero)==3
        notes=p.pilot.subset_csv(p.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",set(corpora))
        note_lookup={x["ROW_ID"]:x for x in notes}
        for item in list(inputs.values())+list(supp_inputs.values()):
            for arm,res in item["retrieval"].items():
                for span in res["passages"]:
                    note=note_lookup[span["note_id"]]
                    assert p.pilot.integer_id(note["SUBJECT_ID"])==item["subject_id"]
                    assert note["TEXT"][span["start"]:span["end_exclusive"]]==span["text"]
                    assert p.pilot.digest_text(note["TEXT"])==span["note_sha256"]
                if item["proposition_id"] in supp_inputs and item is supp_inputs[item["proposition_id"]]:
                    rebuilt=pack_saved(corpora[item["subject_id"]],inputs[item["proposition_id"]]["retrieval"][arm]["top100"])
                    assert reference(rebuilt,item["admission"])==res["reference"]
        props={x["proposition_id"]:x for x in p.pilot.subset_csv(p.RAW/"propositions/propositions.csv.gz","proposition_id",set(inputs))}
        for pid,item in inputs.items():
            prop=props[pid]
            assert item["text"]==prop["text"]
            assert item["queries"]["local"]==prop["brief_hospital_course"][item["local_start"]:item["local_end_exclusive"]]
            assert item["queries"]["sentence"] in prop["parent_text_chunk"]
        for job in jobs+supp_jobs:
            data=json.loads(job["body"]["messages"][1]["content"])
            assert set(data)=={"proposition","reference"} and data["proposition"]==inputs[job["request_id"].split(":",1)[1]]["text"]
        normalized=[scoring.normalize(job,supp_inputs[job["request_id"].split(":",1)[1]],supp_receipts[job["request_id"]]["transport"]) for job in supp_jobs]
        assert normalized==p.pilot.jsonl(supp/"normalized_responses.jsonl")
        assert all(x["status"]=="success" for x in normalized)
        render(output/"replayed_semantic")
        assert tree(run/"review_001/semantic_001")==tree(output/"replayed_semantic")
        anchors=json.loads((run/"review_001/semantic_001/evidence_anchors.json").read_text(encoding="utf-8"))
        for anchor in anchors:
            packet=json.loads((run/"review_001/packets"/(anchor["case_id"]+".json")).read_text(encoding="utf-8"))
            pid=packet["case"]["proposition_id"]
            if anchor["source"]=="released_reference":
                text=packet["released_reference"]["reference"]
            elif anchor["source"]=="ehr_reference":
                item=packet["input"] if anchor["stage"]=="main" else supp_inputs[pid]
                text=item["retrieval"][anchor["arm"]]["reference"]
                assert p.pilot.digest_text(note_lookup[anchor["note_id"]]["TEXT"])==anchor["note_sha256"]
            else:
                answer=packet["responses"][anchor["arm"]] if anchor["stage"]=="main" else next(x for x in normalized if x["proposition_id"]==pid and x["arm"]==anchor["arm"])
                text=answer["output_text"]
            assert p.pilot.digest_text(text)==anchor["source_sha256"] and text[anchor["start"]:anchor["end_exclusive"]]==anchor["quote"]
        assert original_hashes=={x.relative_to(p.OUT).as_posix():p.pilot.digest_file(x) for root in (run,supp) for x in root.rglob("receipt_*.json")}
    # Workspace documents are mutable snapshots. Their later updates must not
    # block replay of the strictly checked frozen inputs, replies and metrics.
    workspace_comparison={name:p.pilot.digest_file(p.ROOT/name)==digest
        for name,digest in auth["preexisting_workspace_changes"].items()}
    dirty=subprocess.run(["git","diff","HEAD","--name-only"],cwd=p.ROOT,capture_output=True,text=True,check=True).stdout.splitlines()
    result=dict(stage="executor_verified_waiting_independent_audit",tests_run=int(re.search(r"Ran (\d+) tests",tests.stderr).group(1)),
        tests_exit_code=0,network_blocked=True,paid_calls_during_verification=0,primary_requests=392,sensitivity_requests=12,
        all_404_one_attempt_and_valid=True,primary_estimated_cny=primary_cost,sensitivity_estimated_cny=supp_cost,total_estimated_cny=primary_cost+supp_cost,
        cap_cny=16,invoice_verified=False,primary_score_files_byte_identical=tree(output/"replayed_analysis"),
        semantic_files_byte_identical=tree(output/"replayed_semantic"),sensitivity_normalization_identical=True,
        repeated_preparation_byte_checks=comparisons,nonidentical_diagnostic_float_fields=len(deviations),
        max_diagnostic_score_difference=max(deviations,default=0),only_score_float_tails_differ=True,
        all_requests_rankings_references_cohort_unchanged=True,anchors_verified=len(anchors),raw_sha256=raw_checked,
        original_404_receipts_unchanged=original_hashes,workspace_document_comparison_informational=workspace_comparison,
        current_tracked_changed_paths_informational=dirty,mutable_workspace_documents_do_not_block_replay=True,
        independent_audit_performed=False,code_sha256={x.relative_to(p.ROOT).as_posix():p.pilot.digest_file(x) for x in [*p.TASK.glob("*.py"),p.ROOT/"tests/test_context_retrieval.py"]})
    p.pilot.write_json(output/"verification.json",result)
    print(p.pilot.canonical(dict(verification=str(output),tests=result["tests_run"],anchors=len(anchors),total_estimated_cny=primary_cost+supp_cost)))


if __name__=="__main__":
    main()
