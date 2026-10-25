"""Print candidate claims and relevant full-reference blocks for manual source review."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ROOT / "outputs/053_thinking_prior_validation/evaluation_cases.jsonl",
    ROOT / "outputs/052_first_tier_validation/evaluation_cases.jsonl",
    ROOT / "outputs/051_thinking_mode_validation/screen_cases.jsonl",
    ROOT / "outputs/044_incremental_evidence_recovery/planning_001/train_cases.jsonl",
    ROOT / "outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl",
]
STOP = {"patient", "patients", "during", "after", "before", "which", "there", "their", "multiple", "history", "underwent"}


def main(prefixes):
    rows = []
    for source in SOURCES:
        for line in source.read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            x = json.loads(line)
            pid = x.get("id", x.get("proposition_id"))
            if pid and any(pid.startswith(prefix) for prefix in prefixes):
                rows.append((source.name, x))
    seen = set()
    for source, x in rows:
        pid = x.get("id", x.get("proposition_id"))
        if pid in seen:
            continue
        seen.add(pid)
        claim = x.get("claim", x.get("text"))
        reference = x.get("reference", x.get("base"))
        words = {w for w in re.findall(r"[a-z0-9]+", claim.lower()) if len(w) >= 4 and w not in STOP}
        blocks = re.split(r"(?=^\d+\. Date:)", reference, flags=re.M)
        ranked = sorted(blocks, key=lambda b: -len(words & set(re.findall(r"[a-z0-9]+", b.lower()))))
        print("\nID", pid, "SID", x.get("sid", x.get("subject_id")), "GT", x.get("GT"), "SRC", source, "REFLEN", len(reference))
        print("CLAIM", claim)
        for block in ranked[:5]:
            if block.strip():
                print("BLOCK", block[:900].replace("\n", " "))


if __name__ == "__main__":
    main(sys.argv[1:])
