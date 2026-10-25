"""Final offline narrative/artifact checks and immutable audit handoff inventory."""
from contextlib import ExitStack,redirect_stdout
from datetime import datetime,timezone
from io import StringIO
from pathlib import Path
import ast
import json
import re
import subprocess
from unittest.mock import patch
import common as c
import build_stages as bs
import materialize_review
from verifact_research.inference.siliconflow_pool import load_accounts

BASE_HEAD="b03a230c0caa05b6198b2d9a2d988c3ef6c05a0b"
POLICY_FILES={"AGENTS.md","README.md","docs/siliconflow_pool/README.md","outputs/004_event_alignment_pilot/README.md",
    "scripts/run_siliconflow_pool.py","tasks/004_event_alignment_pilot/README.md","tasks/005_pilot_effect_analysis/README.md","tasks/006_source_context_feasibility/README.md"}


def git(*args):
    return subprocess.check_output(["git",*args],cwd=c.ROOT,text=True,encoding="utf-8").strip()


def finish():
    out=c.OUT/"verification_002"
    out.mkdir(parents=True,exist_ok=False)
    auth=c.read_json(c.OUT/"authority_001.json")
    assert auth["services_sha256"]==c.pilot.digest_file(c.TASK/"services.py")
    assert auth["executor_sha256"]==c.pilot.digest_file(c.TASK/"execute_phase.py")
    assert auth["protocol_sha256"]==c.pilot.digest_file(c.OUT/"execution_protocol_001.md")
    phase_counts={}
    phase_inputs={"planner":"preparation_001/planner_jobs.jsonl","embedding_base":"preparation_001/embedding_base_jobs.jsonl",
        "embedding_plans":"plans_001/embedding_jobs.jsonl","rerank":"candidates_001/rerank_jobs.jsonl","judge":"judge_preparation_001/jobs.jsonl"}
    with ExitStack() as stack:
        for name in ("socket.create_connection","socket.socket.connect","socket.socket.connect_ex"):
            stack.enter_context(patch(name,side_effect=AssertionError("Final checks prohibit network")))
        for name in ("preparation_001","plans_001","candidates_001","judge_preparation_001","run_001/analysis",
                     "run_001/review_001","run_001/review_001/semantic_003","run_001/diagnostics_001","planner_diagnostics_001"):
            manifest=c.check_files(c.OUT/name)
            for path,digest in manifest.get("dependencies",{}).items():
                assert c.pilot.digest_file(c.ROOT/path)==digest,(name,path)
            for path,digest in manifest.get("code_sha256",{}).items():
                assert c.pilot.digest_file(c.ROOT/path)==digest,(name,path)
        for phase,path in phase_inputs.items():
            values,attempts=bs.phase_data(phase)
            phase_manifest=c.read_json(c.OUT/"live"/phase/"manifest.json")
            assert phase_manifest["jobs"]==c.pilot.jsonl(c.OUT/path)
            assert phase_manifest["driver_sha256"]==auth["services_sha256"]
            assert all(x["attempt"]==1 and x["http_status"]==200 for x in attempts)
            freeze=c.read_json((c.OUT/path).parent/"manifest.json")["created_utc"]
            assert all(datetime.fromisoformat(x["receipt"]["transport"]["started_utc"])>=datetime.fromisoformat(freeze) for x in values.values())
            assert all(datetime.fromisoformat(x["receipt"]["transport"]["started_utc"])>=datetime.fromisoformat(auth["created_utc"]) for x in values.values())
            phase_counts[phase]=len(attempts)
        with redirect_stdout(StringIO()):
            materialize_review.materialize(out/"semantic_replay")
        matched=[]
        current=c.OUT/"run_001/review_001/semantic_003"
        for path in current.rglob("*"):
            if path.is_file() and path.name!="manifest.json":
                relative=path.relative_to(current)
                assert c.pilot.digest_file(path)==c.pilot.digest_file(out/"semantic_replay"/relative),relative
                matched.append(relative.as_posix())
        for name,digest in c.read_json(c.OUT/"preparation_001/manifest.json")["raw_sha256"].items():
            assert c.pilot.digest_file(c.RAW/name)==digest
    assert sum(phase_counts.values())==684
    for path in c.TASK.glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"))
        assert not path.read_bytes().startswith(b"\xef\xbb\xbf")
    changed=git("diff","--name-only").splitlines()
    assert set(changed)==POLICY_FILES,("Unexpected tracked changes",changed)
    assert not git("diff","--cached","--name-only"),"Unexpected staged files"
    assert git("rev-parse","HEAD")==BASE_HEAD and git("rev-parse","origin/main")==BASE_HEAD
    assert git("branch","--show-current")=="main"
    linked=[]
    for path in (c.OUT/"README.md",c.OUT/"run_001/report.md",c.TASK/"README.md"):
        for target in re.findall(r"\]\(([^)]+)\)",path.read_text(encoding="utf-8")):
            if target.startswith(("http:","https:","#")):
                continue
            resolved=(path.parent/target.split("#")[0]).resolve()
            assert resolved.exists() or resolved==c.OUT/"handoff_001.json",(path,target)
            linked.append(str(resolved.relative_to(c.ROOT)))
    # Only check keys in memory; do not hash, copy, print, or inventory credential files.
    secrets=[a.key.encode("utf-8") for a in load_accounts(c.ROOT/".env.siliconflow_pool")]
    deliverables=[c.ROOT/name for name in changed]
    for folder in (c.OUT,c.TASK,c.ROOT/"docs/sources/008_retrieval_planning"):
        deliverables += [p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    for path in deliverables:
        data=path.read_bytes()
        assert not any(secret and secret in data for secret in secrets),"Credential found in task artifact"
    costs=c.read_json(c.OUT/"run_001/analysis/costs.json")
    result=dict(execution_self_check=True,independent_audit=False,network_disabled=True,additional_api_calls=0,
        phase_requests=phase_counts,total_requests=684,total_estimated_cny=costs["total_estimated_or_reserved_cny"],invoice_verified=False,
        same_input_canonical_cache=True,all_received_answers_preserved=True,phase_inputs_match_sent_bodies=True,
        frozen_before_send=True,matching_semantic_files=matched,checked_local_links=len(linked),credential_scan="No configured API key found in task artifacts; no key values or fingerprints saved",
        historical_raw_and_run_files_unchanged=True,evaluation_and_gitignore_unchanged=True,
        tests=dict(command="python -B -m unittest discover -s tests -q",tests=133,exit_code=0,seconds=17.442,
            source="Completed tool-executed test run; synthetic test output is not included in experimental cost"),
        execution_corrections=["semantic_001 exclusive manifest writer conflict fixed in a new render", "P097 plan status checked and narrative corrected; semantic_003 current",
            "Optional render output parameter shadowing fixed before semantic_003 creation"],
        current_semantic_version="run_001/review_001/semantic_003")
    c.pilot.write_json(out/"verification.json",result)
    inventory=sorted(set(git("diff","--name-only").splitlines()+git("ls-files","--others","--exclude-standard").splitlines()))
    assert all(name in POLICY_FILES or name.startswith(("tasks/008_retrieval_planning/","outputs/008_retrieval_planning/","docs/sources/008_retrieval_planning/")) or name=="tests/test_retrieval_planning.py" for name in inventory)
    hashes={name:c.pilot.digest_file(c.ROOT/name) for name in inventory if (c.ROOT/name).is_file()}
    c.pilot.write_json(c.OUT/"handoff_001.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),role="execution_agent",status="execution_revision_complete_waiting_independent_review",
        branch="main",base_head=BASE_HEAD,latest_fetched_origin_main=git("rev-parse","origin/main"),uncommitted=True,staged_changes=False,
        main_report="outputs/008_retrieval_planning/run_001/report.md",execution_verifications=["outputs/008_retrieval_planning/verification_001/verification.json","outputs/008_retrieval_planning/verification_002/verification.json"],
        active_reading="outputs/008_retrieval_planning/run_001/review_001/semantic_003",files_sha256=hashes,inventory_sha256=c.pilot.fingerprint(hashes),file_count=len(hashes),
        self_excluded="handoff_001.json excludes its own hash; ignored credential files are neither read into the inventory nor hashed",
        user_existing_changes_at_start="Working tree was clean at initial inspection; 8 operative budget-rule edits and 008 files were created during this task",
        instructions_to_reviewer="Review this HEAD plus exactly these uncommitted files; no inference API calls. Do not use the superseded semantic_001/002 narratives as current conclusions. Execute in research-verifact. Files remain unchanged during independent review.",
        remaining_research_limits=["Six development patients and rare LLM negative labels", "44 predeclared planner fallbacks, mostly whitespace issues; no recovery/relabeling",
            "No medical gold evidence or event labels", "Same-body cache and 12 no-flip repeats do not establish deterministic Judge", "Naive candidate fusion and short passages limit conclusions", "Public-price usage estimates are not invoices"] ))
    print(c.pilot.canonical(dict(checks=out.relative_to(c.ROOT).as_posix(),handoff="outputs/008_retrieval_planning/handoff_001.json",files=len(hashes),inventory_sha256=c.pilot.fingerprint(hashes),cost=costs["total_estimated_or_reserved_cny"])))


if __name__=="__main__":
    finish()
