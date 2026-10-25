"""Local execution self-check: tests, raw-receipt rescore, hashes and secret exclusion."""
from __future__ import annotations

import argparse
import gzip
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
from unittest.mock import patch

import analyze_live
import pilot
import siliconflow as sf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    out = pilot.new_run(pilot.OUT / "verification_live", None, pilot.ROOT / "data/00_raw")
    # Hash historical files before any test or replay; the new verification lives
    # in its own directory and is not part of this historical snapshot.
    paths = [p for directory in (pilot.ROOT / "data/00_raw", pilot.OUT, pilot.ROOT / "reviews")
        for p in directory.rglob("*") if p.is_file() and not p.is_relative_to(out) and p.suffix != ".pyc"]
    paths += [pilot.ROOT / ".gitignore", pilot.ROOT / "outputs/003_error_analysis/patient_groups.json"]
    before = {p.relative_to(pilot.ROOT).as_posix(): pilot.digest_file(p) for p in sorted(set(paths))}
    pilot.write_json(out / "pre_existing_sha256.json", before)
    test_code = (
        "import sys, unittest\nfrom unittest.mock import patch\n"
        "with patch('socket.socket.connect', side_effect=AssertionError('Network disabled')), "
        "patch('socket.socket.connect_ex', side_effect=AssertionError('Network disabled')), "
        "patch('socket.create_connection', side_effect=AssertionError('Network disabled')):\n"
        "    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))\n"
        "sys.exit(not result.wasSuccessful())\n")
    tests = subprocess.run([sys.executable, "-B", "-c", test_code],
        cwd=pilot.ROOT, capture_output=True, text=True, encoding="utf-8", errors="strict")
    with (out / "tests.log").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(tests.stdout + tests.stderr)
    pilot.require(tests.returncode == 0, "Regression tests failed; see local tests.log")
    with patch("socket.socket.connect", side_effect=AssertionError("Network disabled")), \
            patch("socket.socket.connect_ex", side_effect=AssertionError("Network disabled")), \
            patch("socket.create_connection", side_effect=AssertionError("Network disabled")):
        analyze_live.analyze(run, out / "replay", make_report=True)
    same = {}
    for file in (run / "analysis").iterdir():
        if file.name in {"manifest.json", "analysis_scope.json", "response_checks.json", "fictional_api_cost.json"} or not file.is_file():
            continue
        other = out / "replay" / file.name
        same[file.name] = other.exists() and pilot.digest_file(file) == pilot.digest_file(other)
    pilot.require(same and all(same.values()), "Raw-response replay changed a machine result")
    scope_a = json.loads((run / "analysis/analysis_scope.json").read_text(encoding="utf-8"))
    scope_b = json.loads((out / "replay/analysis_scope.json").read_text(encoding="utf-8"))
    scope_a.pop("registered_utc"); scope_b.pop("registered_utc")
    pilot.require(scope_a == scope_b, "Analysis scope changed beyond replay timestamp")
    checks_a = json.loads((run / "analysis/response_checks.json").read_text(encoding="utf-8"))
    checks_b = json.loads((out / "replay/response_checks.json").read_text(encoding="utf-8"))
    workspace_changes = checks_b.pop("protected_files_changes")
    pilot.require(checks_b.pop("protected_files_policy") == "workspace_snapshot_nonblocking", "Unexpected workspace policy")
    pilot.require(checks_b.pop("original_receipt_hashes_verified") is True, "Original receipt hashes not checked")
    pilot.require(checks_b.pop("protected_files_unchanged") == (not workspace_changes), "Inconsistent workspace diagnostic")
    checks_a.pop("protected_files_unchanged")
    pilot.require(checks_a == checks_b, "Response checks changed beyond integrity diagnostics")
    fee_a = json.loads((run / "analysis/fictional_api_cost.json").read_text(encoding="utf-8"))
    fee_b = json.loads((out / "replay/fictional_api_cost.json").read_text(encoding="utf-8"))
    pilot.require(fee_a == {k: fee_b[k] for k in fee_a}, "Bound fictional cost differs from original result")
    original_manifest = json.loads((run / "analysis/manifest.json").read_text(encoding="utf-8"))
    for name, digest in original_manifest["source_receipts_sha256"].items():
        pilot.require(pilot.digest_file(run / name) == digest, "Receipt changed after first analysis")
    for name, digest in original_manifest["output_sha256"].items():
        pilot.require(pilot.digest_file(run / "analysis" / name) == digest, "Analysis output changed")
    # Never report the credential, its hash, length or any matching file contents.
    secret = sf.load_key().encode("utf-8")
    paths = [*run.rglob("*"), *(pilot.OUT / "api_preflight").rglob("*"), *out.rglob("*"),
        *pilot.TASK.rglob("*"), pilot.ROOT / "README.md", pilot.ROOT / "AGENTS.md", pilot.OUT / "README.md",
        pilot.ROOT / "tests/test_siliconflow_pilot.py", pilot.ROOT / "tests/test_live_analysis.py"]
    count, clean = 0, True
    for path in sorted(set(paths)):
        if not path.is_file() or path.suffix == ".pyc":
            continue
        raw = path.read_bytes()
        clean = clean and secret not in raw
        if path.suffix == ".gz":
            clean = clean and secret not in gzip.decompress(raw)
        count += 1
    del secret
    pilot.require(clean, "Credential detected in task artifacts; do not publish artifacts")
    unchanged = all((pilot.ROOT / name).is_file() and pilot.digest_file(pilot.ROOT / name) == digest for name, digest in before.items())
    pilot.require(unchanged, "Pre-existing raw, historical, review or split file changed during verification")
    versions = {name: importlib.metadata.version(name) for name in ("duckdb", "numpy", "pandas", "scipy", "scikit-learn", "irrCAC")}
    code = [Path(__file__), Path(analyze_live.__file__), analyze_live.REPLAY_BINDINGS, pilot.ROOT / "tests/test_live_analysis.py"]
    pilot.write_json(out / "verification.json", dict(status="execution_revision_complete_awaiting_independent_review",
        tests_exit_code=tests.returncode, machine_files_byte_identical=same,
        tests_run=int(re.search(r"Ran (\d+) tests", tests.stderr).group(1)), network_connections_blocked=True,
        pre_existing_files_unchanged=unchanged, pre_existing_file_count=len(before),
        metadata_only_changes={"response_checks.json": "Nonblocking workspace diagnostics and pinned receipt verification",
            "fictional_api_cost.json": "Unchanged amount; added fixed source identities and hashes",
            "analysis_scope.json": "Replay timestamp only", "manifest.json": "Replay time, revised analysis code and output hashes"},
        workspace_snapshot_changes=workspace_changes, fictional_api_cost_unchanged=True,
        original_report_byte_identical=same["report.md"],
        source_receipt_hashes_verified=True, credential_scan_clean=clean, credential_scanned_files=count,
        independent_audit_performed=False, new_external_inference_calls=0,
        python=sys.version, platform=platform.platform(), dependency_versions=versions,
        verifier_code_sha256=pilot.digest_file(Path(__file__)),
        revision_code_sha256={p.relative_to(pilot.ROOT).as_posix(): pilot.digest_file(p) for p in code}))
    print(pilot.canonical(dict(verification=str(out), identical_machine_files=len(same),
        tests_exit_code=tests.returncode, credential_scan_clean=clean, independent_audit_performed=False)))


if __name__ == "__main__":
    main()
