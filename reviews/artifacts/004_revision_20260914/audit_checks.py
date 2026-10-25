"""Independent offline follow-up of 004; writes only to an isolated directory.

Usage: python -B audit_checks.py REPOSITORY EXISTING_AUDIT_TEMP_DIRECTORY
The supplied temporary directory must contain the initial version_snapshot.json.
No credentials are loaded. No inference or production verifier is invoked.
"""
from __future__ import annotations

import contextlib
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(sys.argv[1]).resolve()
AUDIT = Path(sys.argv[2]).resolve()
RUN_REL = Path("outputs/004_event_alignment_pilot/run_003")
TASK_REL = Path("tasks/004_event_alignment_pilot")
RUN = ROOT / RUN_REL
started = datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


blocked_calls = []


def no_network(*args, **kwargs):
    blocked_calls.append("network_attempt_blocked")
    raise AssertionError("Independent audit forbids network connections")


results = {"stage": "independent_revision_review", "started_utc": started,
           "base_head": "a282c70698b79a890b279391739a4c20e851d9a5",
           "version_snapshot": read(AUDIT / "version_snapshot.json"), "tamper_checks": []}


def compare_replay(new):
    old = RUN / "analysis"
    allowed = {"manifest.json", "analysis_scope.json", "response_checks.json", "fictional_api_cost.json"}
    same = {p.name: sha(p) == sha(new / p.name) for p in old.iterdir() if p.is_file() and p.name not in allowed}
    assert len(same) == 15 and all(same.values()), same
    left, right = read(old / "analysis_scope.json"), read(new / "analysis_scope.json")
    left.pop("registered_utc")
    right.pop("registered_utc")
    assert left == right
    left, right = read(old / "response_checks.json"), read(new / "response_checks.json")
    changes = right.pop("protected_files_changes")
    assert right.pop("protected_files_policy") == "workspace_snapshot_nonblocking"
    assert right.pop("original_receipt_hashes_verified") is True
    assert right.pop("protected_files_unchanged") == (not changes)
    left.pop("protected_files_unchanged")
    assert left == right
    left, right = read(old / "fictional_api_cost.json"), read(new / "fictional_api_cost.json")
    assert left == {k: right[k] for k in left}
    manifest = read(new / "manifest.json")
    assert all(sha(new / n) == d for n, d in manifest["output_sha256"].items())
    assert manifest["source_receipts_sha256"] == read(old / "manifest.json")["source_receipts_sha256"]
    return {"byte_identical_files": same, "workspace_diagnostics": changes,
            "remaining_differences_limited_to_declared_metadata": True}


def reject_change(path, operation, function, expected_text):
    assert path.is_relative_to(AUDIT / "shadow"), "Mutation escaped isolated copy"
    before = path.read_bytes() if path.exists() else None
    try:
        if operation == "append":
            path.write_bytes(before + b"\n")
        elif operation == "remove":
            path.unlink()
        else:
            path.write_bytes(operation)
        try:
            function()
        except (ValueError, FileNotFoundError) as exc:
            assert expected_text in str(exc), (path.name, type(exc).__name__, str(exc))
            results["tamper_checks"].append({"path": path.relative_to(AUDIT / "shadow").as_posix(),
                "operation": operation if isinstance(operation, str) else "extra_receipt",
                "rejected": True, "exception": type(exc).__name__, "expected_error": expected_text})
        else:
            raise AssertionError("Accepted altered material: " + path.relative_to(AUDIT / "shadow").as_posix())
    finally:
        if before is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(before)


with contextlib.ExitStack() as guard:
    for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
        guard.enter_context(patch(target, side_effect=no_network))
    sys.path.insert(0, str(ROOT / TASK_REL))
    sys.path.insert(0, str(ROOT / "src"))
    with (AUDIT / "tests.log").open("x", encoding="utf-8", newline="\n") as log:
        with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
            tested = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    results["existing_tests"] = {"run": tested.testsRun, "failures": len(tested.failures),
                                 "errors": len(tested.errors), "successful": tested.wasSuccessful()}
    assert tested.wasSuccessful()
    print("Existing tests independently completed:", tested.testsRun, flush=True)

    import analyze_live as analysis
    import live
    import pilot
    import resume_balance

    assert pilot.ROOT == ROOT
    frozen, original = read(RUN / "manifest.json"), read(RUN / "analysis/manifest.json")
    results["frozen_files_independently_verified"] = len(frozen["output_sha256"])
    assert all(sha(RUN / n) == d for n, d in frozen["output_sha256"].items())
    results["frozen_code_independently_verified"] = len(frozen["code_sha256"])
    assert all(sha(ROOT / n) == d for n, d in frozen["code_sha256"].items())
    assert all(sha(RUN / n) == d for n, d in original["source_receipts_sha256"].items())
    assert all(sha(RUN / "analysis" / n) == d for n, d in original["output_sha256"].items())
    results["original_source_files_verified"] = len(original["source_receipts_sha256"])
    results["original_analysis_outputs_verified"] = len(original["output_sha256"])

    with contextlib.redirect_stdout(io.StringIO()):
        analysis.analyze(RUN, AUDIT / "baseline_replay", make_report=True)
    results["baseline_replay"] = compare_replay(AUDIT / "baseline_replay")
    print("Original-workspace offline replay matched 15 result files", flush=True)

    shadow = AUDIT / "shadow"
    shadow.mkdir()
    shadow_run = shadow / RUN_REL
    shutil.copytree(RUN, shadow_run)
    source_rel = Path("outputs/004_event_alignment_pilot/run_001")
    shutil.copytree(ROOT / source_rel, shadow / source_rel)
    api_rel = Path("outputs/004_event_alignment_pilot/api_preflight")
    shutil.copytree(ROOT / api_rel, shadow / api_rel)
    preflight = read(RUN / "preflight.json")
    copies = set(frozen["code_sha256"]) | set(preflight["protected_files_sha256"]) | {
        "README.md", "AGENTS.md", "tasks/004_event_alignment_pilot/README.md",
        "outputs/004_event_alignment_pilot/README.md", "tasks/004_event_alignment_pilot/replay_bindings.json",
        "tasks/004_event_alignment_pilot/resume_balance.py"}
    for name in sorted(copies):
        assert (ROOT / name).resolve().is_relative_to(ROOT) and Path(name).name != ".env"
        src, dst = ROOT / name, shadow / name
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    with contextlib.ExitStack() as sandbox:
        sandbox.enter_context(patch.object(pilot, "ROOT", shadow))
        sandbox.enter_context(patch.object(pilot, "OUT", shadow / "outputs/004_event_alignment_pilot"))
        sandbox.enter_context(patch.object(live, "SOURCE", shadow / source_rel))
        sandbox.enter_context(patch.object(analysis, "REPLAY_BINDINGS", shadow / TASK_REL / "replay_bindings.json"))
        sandbox.enter_context(patch.object(resume_balance, "__file__", str(shadow / TASK_REL / "resume_balance.py")))
        baseline_fee = analysis.fictional_api_cost(shadow_run)
        assert len(baseline_fee["sources"]) == 2
        assert baseline_fee["sources"][1]["sha256"] == preflight["fictional_preflight_summary_sha256"]
        api = shadow / api_rel
        probe = read(api / "run_001/normalized.json")["cost"]["cny"]
        checks = [read(p)["normalized"]["cost"]["cny"] for p in (api / "run_002").glob("fictional-*.json")]
        assert len(checks) == 21
        total = Decimal(str(probe)) + sum((Decimal(str(v)) for v in checks), Decimal(0))
        assert abs(total - Decimal(str(baseline_fee["estimated_cny"]))) < Decimal("1e-12")
        results["fictional_cost"] = {"probe_responses": 1, "three_arm_responses": len(checks),
            "independently_summed_estimated_cny": str(total), "bound_sources": baseline_fee["sources"],
            "preflight_pin_matches": True, "settlement_verified": False}

        changed_docs = ["README.md", "AGENTS.md", "reviews/README.md", "reviews/004_event_alignment_pilot.md",
                        "tasks/004_event_alignment_pilot/README.md", "outputs/004_event_alignment_pilot/README.md"]
        for name in changed_docs:
            p = shadow / name
            p.write_bytes(p.read_bytes() + b"\nIndependent audit: ordinary current-status update.\n")
        (shadow / ".vscode/settings.json").unlink()
        later = api / "run_999"
        later.mkdir()
        write(later / "summary.json", {"cost_estimate_cny": 1000})
        write(later / "normalized.json", {"cost": {"cny": 2000}})
        assert analysis.fictional_api_cost(shadow_run) == baseline_fee
        with contextlib.redirect_stdout(io.StringIO()):
            analysis.analyze(shadow_run, AUDIT / "changed_documents_replay", make_report=True)
        results["changed_documents_and_future_cost_replay"] = compare_replay(AUDIT / "changed_documents_replay")
        results["simulated_doc_changes"] = changed_docs + [".vscode/settings.json removed"]
        results["future_unrelated_cost_ignored_cny"] = 3000
        print("Changed-document and unrelated-cost replay also matched 15 files", flush=True)

        collect = lambda: analysis.collect(shadow_run)
        reject_change(shadow_run / "manifest.json", "append", collect, "Unregistered frozen run")
        for name in frozen["output_sha256"]:
            reject_change(shadow_run / name, "append", collect, "Frozen input changed")
        for name in frozen["code_sha256"]:
            reject_change(shadow / name, "append", collect, "Inference code/settings changed")
        for name in ("analysis/manifest.json",):
            for op in ("append", "remove"):
                reject_change(shadow_run / name, op, collect, "Original analysis manifest changed or missing")
        for name in ("attempt_starts.jsonl", "balance_recovery.json"):
            reject_change(shadow_run / name, "append", collect, "Saved receipt/start/recovery file changed or missing")
        receipt = next((shadow_run / "receipts").glob("*.json"))
        for op in ("append", "remove"):
            reject_change(receipt, op, collect, "Saved receipt/start/recovery file changed or missing")
        reject_change(shadow_run / "receipts/independent_extra.json", receipt.read_bytes(), collect, "Unresolved sent request without receipt")
        reject_change(shadow / TASK_REL / "resume_balance.py", "append", collect, "Recovery code changed")
        for item in baseline_fee["sources"]:
            for op in ("append", "remove"):
                reject_change(shadow / item["path"], op, lambda: analysis.fictional_api_cost(shadow_run), "Fictional cost source changed or missing")
        assert analysis.fictional_api_cost(shadow_run) == baseline_fee
        print("Independent tamper rejection cases completed:", len(results["tamper_checks"]), flush=True)

    with (RUN / "cohort_llm.csv").open(encoding="utf-8", newline="") as f:
        llm = list(csv.DictReader(f))
    with (RUN / "cohort_human.csv").open(encoding="utf-8", newline="") as f:
        human = list(csv.DictReader(f))
    patients = {r["subject_id"] for r in llm + human}
    groups = read(ROOT / "outputs/003_error_analysis/patient_groups.json")["groups"]
    assert len(llm) == 181 and len(human) == 240 and len(patients) == 6
    assert patients <= set(groups["development"]) and not patients & set(groups["reserved_test"])
    results["scope"] = {"llm": len(llm), "human": len(human), "patients": len(patients),
        "development_only": True, "reserved_test_case_inspection": False}
    results["status_preserved"] = read(RUN / "analysis/status.json")
    results["analysis_scope_preserved"] = read(RUN / "analysis/analysis_scope.json")
    prior = read(ROOT / "outputs/004_event_alignment_pilot/verification_live/run_002/pre_existing_sha256.json")
    results["pre_existing_mismatches_after_audit"] = [n for n, d in prior.items() if not (ROOT / n).is_file() or sha(ROOT / n) != d]
    results["reviewed_version_mismatches_after_audit"] = [n for n, d in results["version_snapshot"]["files_sha256"].items() if sha(ROOT / n) != d]
    assert not results["pre_existing_mismatches_after_audit"] and not results["reviewed_version_mismatches_after_audit"]
    results["network_guard_attempts"] = blocked_calls
    assert not blocked_calls
    results["dependency_versions"] = {n: importlib.metadata.version(n) for n in ("duckdb", "pypdf", "fonttools", "numpy", "pandas", "scipy", "scikit-learn", "irrCAC")}
    results["finished_utc"] = datetime.now(timezone.utc).isoformat()
    results["result"] = "PASS: two prior revision issues close; research limitations retained"
    write(AUDIT / "evidence.json", results)
    print(json.dumps({"result": results["result"], "existing_tests": tested.testsRun,
        "independent_tamper_cases": len(results["tamper_checks"]), "historical_files_unchanged": len(prior),
        "no_network_attempts": not blocked_calls, "evidence": str(AUDIT / "evidence.json")}, ensure_ascii=False), flush=True)
