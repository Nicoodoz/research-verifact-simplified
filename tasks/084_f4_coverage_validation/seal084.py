"""Create a deterministic, read-only handoff hash manifest after 084 closure."""
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/084_f4_coverage_validation"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = OUT / "handoff_manifest.json"
    assert not target.exists()
    attempts = sorted((OUT / "attempts").glob("*/request.json"))
    assert len(attempts) == 360
    h = hashlib.sha256()
    for request in attempts:
        receipt = request.parent / "receipt.json"
        assert receipt.exists()
        for path in (request, receipt):
            rel = path.relative_to(ROOT).as_posix()
            h.update(rel.encode("utf-8") + b"\0" + sha(path).encode("ascii") + b"\n")
    task_files = sorted((ROOT / "tasks/084_f4_coverage_validation").glob("*"))
    output_files = sorted(p for p in OUT.glob("*") if p.is_file() and p != target)
    shared = [ROOT / p for p in ("AGENTS.md", "README.md", "docs/PROJECT_STATUS.md", "docs/API_POLICY.md", "docs/RESEARCH_EXECUTION.md")]
    paths = [p for p in task_files + output_files + shared if p.is_file()]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    manifest = {"created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "start_and_end_HEAD": head, "commit_or_push_performed": False,
                "attempt_pairs": len(attempts), "attempt_files": 2*len(attempts),
                "attempt_tree_sha256": h.hexdigest(),
                "files_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths},
                "note": "Files are hashed by bytes; attempt tree hash uses sorted relative path, NUL, hex SHA256, newline. Historical source hashes are in freeze.json and 083_oof_diagnosis.json."}
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
    print(json.dumps({"files":len(paths),"attempts":len(attempts),"head":head,"attempt_tree_sha256":h.hexdigest()}))


if __name__ == "__main__":
    main()
