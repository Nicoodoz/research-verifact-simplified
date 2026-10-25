"""Repeatability and provenance checks; no new dataset-wide audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from analyze import ROOT, RAW, OUT, FORMAL, digest_file, load_split, new_run, require, write_json


def compare(a: Path, b: Path) -> int:
    ma = json.loads((a / "manifest.json").read_text(encoding="utf-8"))["output_sha256"]
    mb = json.loads((b / "manifest.json").read_text(encoding="utf-8"))["output_sha256"]
    require(ma == mb, f"Repeated artifacts differ: {a} / {b}")
    for p, sha in ma.items():
        require(digest_file(a / p) == sha == digest_file(b / p), f"Changed artifact: {p}")
    return len(ma)


def verify(a: str, b: str, ar: str, br: str) -> None:
    for name in (a, b, ar, br):
        require(re.fullmatch(r"(?:run|review)_\d{3,}", name) is not None, "Invalid directory name")
    load_split()
    extraction_n = compare(OUT / a, OUT / b)
    review_n = compare(OUT / a / ar, OUT / b / br)
    baseline = json.loads((FORMAL / "manifest.json").read_text(encoding="utf-8"))["input_sha256"]
    require(all(digest_file(RAW / p) == sha for p, sha in baseline.items()), "Raw release changed since 002")
    index = 1
    while (OUT / f"verification_{index:03d}").exists():
        index += 1
    output = new_run(OUT, f"verification_{index:03d}", ROOT / "data/00_raw")
    planned_record = (output / "verification.json").resolve()
    checked_links = 0
    for p in [OUT / "README.md", OUT / a / ar / "report.md", *(OUT / a / ar / "cases").glob("*.md")]:
        for target in re.findall(r"\]\(([^)]+)\)", p.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+://|#", target):
                continue
            resolved = (p.parent / target.split("#")[0]).resolve()
            require(resolved.exists() or resolved == planned_record, f"Broken link: {p}: {target}")
            checked_links += 1
    # The index links to this record, so verify its existence after creating it below.
    tests = subprocess.run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", timeout=120)
    log = tests.stdout + tests.stderr
    (output / "tests.log").write_text(log, encoding="utf-8", newline="\n")
    require(tests.returncode == 0, "Tests failed; see local tests.log")
    match = re.search(r"Ran (\d+) tests", log)
    result = dict(status="pass", extraction_files_identical=extraction_n, review_files_identical=review_n,
        compared=[a + "/" + ar, b + "/" + br], unchanged_raw_files=len(baseline),
        checked_links=checked_links,
        unit_tests=int(match.group(1)) if match else None, tests_exit_code=tests.returncode,
        partition_sha256=digest_file(OUT / "patient_groups.json"),
        git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        code_sha256={str(p.relative_to(ROOT)).replace('\\', '/'): digest_file(p) for p in [*(ROOT / "tasks/003_error_analysis").glob("*.py"), ROOT / "tests/test_error_analysis.py"]},
        scope="Reproducibility/provenance checks only; clinical interpretations are not independently validated.")
    write_json(output / "verification.json", result)
    require(planned_record.exists(), "Verification record was not written")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-a", default="run_001")
    p.add_argument("--run-b", default="run_002")
    p.add_argument("--review-a", default="review_004")
    p.add_argument("--review-b", default="review_003")
    args = p.parse_args()
    verify(args.run_a, args.run_b, args.review_a, args.review_b)
