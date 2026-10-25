"""Verify two task-002 runs and replay both profiles through the public CLI."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.audit.common import digest_file, write_json


def checked_manifest(run: Path) -> dict:
    manifest = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["output_sha256"].items():
        if digest_file(run / name) != expected:
            raise ValueError(f"Output hash mismatch: {run / name}")
    actual = {p.relative_to(run).as_posix() for p in run.rglob("*") if p.is_file() and p.name != "manifest.json"}
    if actual != set(manifest["output_sha256"]):
        raise ValueError(f"Run contains unrecorded or absent files: {run}")
    for key in ["raw_unchanged", "raw_matches_001", "official_checksums_match"]:
        if manifest[key] is not True:
            raise ValueError(f"{run}: {key} did not pass")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Verification output already exists; choose a new filename")
    if (ROOT / "data/00_raw").resolve() in args.output.resolve().parents:
        raise ValueError("Verification output cannot be in raw data")
    first, second = checked_manifest(args.first), checked_manifest(args.second)
    if first["input_sha256"] != second["input_sha256"]:
        raise ValueError("Reproduction runs used different releases")
    used_code = lambda m: {k: v for k, v in m["code_and_config_sha256"].items()
                           if k.startswith("src/") or k.endswith("paper_targets.json") or k == "environment.yml"}
    if used_code(first) != used_code(second):
        raise ValueError("Analysis implementation, targets, or environment changed between runs")
    compared = []
    for name, digest in first["output_sha256"].items():
        if Path(name).suffix in {".csv", ".json"}:
            if digest != second["output_sha256"].get(name):
                raise ValueError(f"Nondeterministic machine result: {name}")
            compared.append(name)
    if set(first["output_sha256"]) != set(second["output_sha256"]):
        raise ValueError("Runs produced different artifact sets")
    report1 = (args.first / "report.md").read_text(encoding="utf-8").replace(args.first.name, "RUN")
    report2 = (args.second / "report.md").read_text(encoding="utf-8").replace(args.second.name, "RUN")
    if report1 != report2:
        raise ValueError("Reports differ beyond their run name")
    raw = ROOT / "data/00_raw/verifact-bhc/1.1.0"
    current = {p.relative_to(raw).as_posix(): digest_file(p) for p in sorted(raw.rglob("*")) if p.is_file()}
    if current != second["input_sha256"]:
        raise ValueError("Raw release changed after reproduction")
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
                           cwd=ROOT, capture_output=True, text=True, check=True)
    log = tests.stdout + tests.stderr
    log_path = args.output.with_suffix(".tests.txt")
    with log_path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(log)
    replay = []
    for validity, profile, source in [("all", "paper_item", "ai_metrics.json"),
                                      ("valid_only", "research_patient", "research_baselines.json")]:
        pred = args.second / f"baseline_predictions/R1-70B_llm_claim_{validity}.csv"
        command = [sys.executable, "-B", "scripts/evaluate_predictions.py", "--method-name", "R1-70B verification replay",
                   "--cohort", str(args.second / f"cohorts/llm_claim_{validity}.csv"), "--predictions", str(pred),
                   "--validity", validity, "--profile", profile, "--bootstrap", str(second["parameters"]["bootstrap"])]
        if profile == "research_patient":
            command += ["--baseline-predictions", str(pred)]
        else:
            # The bulk paper reproduction explicitly records available-case policy;
            # use that same policy when comparing complete result metadata as well.
            command += ["--missing", "available"]
        process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        directory = Path(process.stdout.splitlines()[0])
        observed = json.loads((directory / "metrics.json").read_text(encoding="utf-8"))
        records = json.loads((args.second / source).read_text(encoding="utf-8"))
        expected = next(r["evaluation"] for r in records if all(r["configuration"][k] == v for k, v in
                        dict(model="R1-70B", author_type="llm", proposition_type="claim", fact_type="sentence", top_n="100").items()))
        if observed != expected:
            raise ValueError("Public CLI and reproduction runner returned different evaluations")
        if profile == "research_patient":
            paired = json.loads((directory / "paired_comparison.json").read_text(encoding="utf-8"))
            if any(v["delta"] != 0 or v["ci95"] != [0., 0.] for v in paired["metrics"].values()):
                raise ValueError("Identical-method paired comparison is not exactly zero")
        replay.append(dict(profile=profile, validity=validity, run=str(directory.relative_to(ROOT)),
                           metrics_equal=True, metrics_sha256=digest_file(directory / "metrics.json")))
    write_json(args.output, dict(verified_utc=datetime.now(timezone.utc).isoformat(), first=str(args.first), second=str(args.second),
                                  compared_machine_files=compared, machine_files_identical=True, reports_equal_except_run_name=True,
                                  raw_files_unchanged=len(current), source_implementation_equal=True,
                                  unit_tests=int(re.search(r"Ran (\d+) tests", log).group(1)), unit_tests_pass=True,
                                  test_log_sha256=digest_file(log_path), cli_replay=replay))
    print(f"Verified {len(compared)} identical machine artifacts, raw files, tests and both public CLI profiles: {args.output}")


if __name__ == "__main__":
    main()
