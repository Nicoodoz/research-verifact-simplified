"""Offline run replay, immutable-receipt checks and executor verification for 006."""
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch

import context_feasibility as cf
import run_context_pilot as execution
import score_context_pilot as scoring
import analyze_context_results as analysis
import finalize_context_review as semantic


def verify_manifest(base, filename, key):
    manifest = json.loads((base / filename).read_text(encoding="utf-8"))
    for name, digest in manifest[key].items():
        cf.pilot.require(cf.pilot.digest_file(base / name) == digest, "Manifest mismatch: " + name)
    return manifest


def equal_tree(left, right):
    first = {p.relative_to(left).as_posix(): cf.pilot.digest_file(p) for p in left.rglob("*") if p.is_file()}
    second = {p.relative_to(right).as_posix(): cf.pilot.digest_file(p) for p in right.rglob("*") if p.is_file()}
    cf.pilot.require(first == second, "Replay differs")
    return first


def main():
    prep, run = cf.OUT / "preparation_001", cf.OUT / "run_001"
    review = run / "review_001"
    output = cf.fresh("verification_live")
    code = ("import sys,unittest\nfrom unittest.mock import patch\n"
        "with patch('socket.socket.connect',side_effect=AssertionError('Network disabled')), "
        "patch('socket.socket.connect_ex',side_effect=AssertionError('Network disabled')), "
        "patch('socket.create_connection',side_effect=AssertionError('Network disabled')):\n"
        "    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))\n"
        "sys.exit(not result.wasSuccessful())\n")
    tests = subprocess.run([sys.executable, "-B", "-c", code], cwd=cf.ROOT, capture_output=True, text=True, encoding="utf-8")
    (output / "tests.log").write_text(tests.stdout+tests.stderr, encoding="utf-8", newline="\n")
    cf.pilot.require(tests.returncode == 0, "Tests failed")
    with patch("socket.socket.connect", side_effect=AssertionError("Network disabled")), patch("socket.socket.connect_ex", side_effect=AssertionError("Network disabled")), patch("socket.create_connection", side_effect=AssertionError("Network disabled")):
        jobs = execution.load_preparation(prep)
        before = {p.name: cf.pilot.digest_file(p) for p in run.glob("receipt_*.json")}
        manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        state = json.loads((run / "state.json").read_text(encoding="utf-8"))
        amendment = json.loads((cf.OUT / "execution_amendment_001.json").read_text(encoding="utf-8"))
        cf.pilot.require(manifest["jobs"] == jobs and manifest["budget_cny"] == 8, "Run does not match frozen requests/budget")
        cf.pilot.require(cf.pilot.fingerprint(manifest) == state["run_id"], "Wrong run ID")
        cf.pilot.require(set(state["jobs"]) == {j["request_id"] for j in jobs}, "Request set differs")
        failures, charges = [], Decimal(0)
        for i, job in enumerate(jobs):
            progress = state["jobs"][job["request_id"]]
            cf.pilot.require(progress["attempts"] == len(progress["receipts"]) == 1, "Unexpected attempt count")
            pointer = progress["receipts"][0]
            cf.pilot.require(pointer["file"] == f"receipt_{i+1:06d}_001.json", "Receipt order differs")
            path = run / pointer["file"]
            cf.pilot.require(cf.pilot.digest_file(path) == pointer["sha256"], "Receipt changed")
            receipt = json.loads(path.read_text(encoding="utf-8"))
            cf.pilot.require(receipt["run_id"] == state["run_id"] and receipt["request_id"] == job["request_id"]
                and receipt["request_sha256"] == cf.pilot.fingerprint(job["body"])
                and receipt["account"] == progress["account"] == pointer["account"]
                and receipt["attempt"] == 1, "Receipt identity differs")
            charge, basis = execution.charge_for(receipt["transport"], job["max_cost_cny"])
            cf.pilot.require(charge == pointer["estimated_charge_cny"] and basis == pointer["charge_basis"], "Charge settlement differs")
            charges += Decimal(str(charge))
            if progress["status"] == "unknown":
                cf.pilot.require(progress == amendment["terminal_unknown"][job["request_id"]], "Unknown result was changed")
                failures.append(dict(request_id=job["request_id"], kind="unknown_transport", receipt=pointer["file"]))
            else:
                cf.pilot.require(progress["status"] == "response_received", "Unsent/service-error work remains")
        cf.pilot.require(abs(float(charges)-state["reserved_budget_cny"]) < 1e-10 and float(charges) < 8, "Budget settlement mismatch")
        cf.pilot.require(len(before) == len(jobs) == 192, "Unexpected extra/missing receipts")
        for request_id, progress in amendment["original_state"]["jobs"].items():
            if progress["status"] in {"unknown", "response_received"}:
                cf.pilot.require(state["jobs"][request_id] == progress, "Pre-continuation result changed")
            else:
                cf.pilot.require(progress["attempts"] == 0, "Continuation included a previously sent job")
        prep_manifest = verify_manifest(prep, "manifest.json", "output_sha256")
        raw_checked = {}
        for name, digest in prep_manifest["raw_sha256"].items():
            actual = cf.pilot.digest_file(cf.RAW / name)
            cf.pilot.require(actual == digest, "Raw input changed")
            raw_checked[name] = actual
        verify_manifest(run / "analysis", "manifest.json", "output_sha256")
        verify_manifest(review, "extraction_manifest.json", "outputs_sha256")
        verify_manifest(review / "semantic_001", "manifest.json", "outputs_sha256")
        scoring.score(prep, run, output / "replayed_analysis")
        scoring_equal = equal_tree(run / "analysis", output / "replayed_analysis")
        analysis.build(prep, run, output / "replayed_review")
        # Compare extraction files only; semantic artifacts are an appended stage.
        extracted = json.loads((review / "extraction_manifest.json").read_text(encoding="utf-8"))["outputs_sha256"]
        extracted_equal = {name: cf.pilot.digest_file(output / "replayed_review" / name) == digest for name, digest in extracted.items()}
        cf.pilot.require(all(extracted_equal.values()), "Case reconstruction differs")
        cf.pilot.require(cf.pilot.digest_file(review / "extraction_manifest.json") == cf.pilot.digest_file(output / "replayed_review/extraction_manifest.json"), "Extraction manifest differs")
        semantic.render(review, output / "replayed_semantic")
        semantic_equal = equal_tree(review / "semantic_001", output / "replayed_semantic")
        cf.pilot.require(before == {p.name: cf.pilot.digest_file(p) for p in run.glob("receipt_*.json")}, "Replay modified original receipt")
        anchors = json.loads((review / "semantic_001/evidence_anchors.json").read_text(encoding="utf-8"))
        for anchor in anchors:
            packet = json.loads((review / "packets" / (anchor["case_id"] + ".json")).read_text(encoding="utf-8"))
            if anchor["source"] == "reference":
                text = packet["input"]["reference"]
            elif anchor["source"] == "full_output":
                text = packet["responses"][anchor["arm"]]["output_text"]
            else:
                text = packet["input"]["source_context"]["text"]
            cf.pilot.require(cf.pilot.digest_text(text) == anchor["source_sha256"] and text[anchor["start"]:anchor["end_exclusive"]] == anchor["quote"], "Anchor mismatch")
        valid = cf.pilot.jsonl(run / "analysis/normalized_responses.jsonl")
        failures.extend(dict(request_id=r["request_id"], kind="invalid_received_output", errors=r["structural_errors"]) for r in valid if r["status"] != "success")
    old_paths = [".gitignore", "environment.yml", "src", "reviews", "data/00_raw"]
    for n in range(1, 6):
        old_paths += [p.relative_to(cf.ROOT).as_posix() for parent in ("tasks", "outputs") for p in (cf.ROOT / parent).glob(f"{n:03d}_*")]
    unchanged = subprocess.run(["git", "diff", "HEAD", "--name-only", "--", *old_paths], cwd=cf.ROOT, text=True, capture_output=True, check=True)
    cf.pilot.require(not unchanged.stdout.strip(), "Pre-existing project files changed")
    cf.pilot.write_json(output / "verification.json", dict(stage="executor_verified_pending_independent_review",
        tests_run=int(re.search(r"Ran (\d+) tests", tests.stderr).group(1)), tests_exit_code=0,
        network_blocked_for_verification=True, new_inference_calls_during_verification=0,
        frozen_request_count=192, actual_attempt_count=192, received_count=len(valid), valid_predictions=sum(r["status"] == "success" for r in valid),
        failures=failures, budget_used_or_reserved_cny=float(charges), budget_limit_cny=8, invoice_verified=False,
        pre_continuation_answers_and_unknowns_unchanged=True, raw_input_hashes=raw_checked,
        scoring_files_byte_identical=scoring_equal, extraction_files_identical=extracted_equal,
        semantic_files_byte_identical=semantic_equal, anchors_verified=len(anchors),
        prior_tasks_reviews_raw_and_evaluation_unchanged=True, independent_audit_performed=False,
        code_sha256={p.relative_to(cf.ROOT).as_posix(): cf.pilot.digest_file(p) for p in [*cf.TASK.glob("*.py"), *cf.ROOT.glob("tests/test_source_context*.py")]},
        receipt_sha256=before, preparation_manifest_sha256=cf.pilot.digest_file(prep / "manifest.json")))
    print(cf.pilot.canonical(dict(verification=str(output), tests="passed", anchors=len(anchors), failures=len(failures))))


if __name__ == "__main__":
    main()
