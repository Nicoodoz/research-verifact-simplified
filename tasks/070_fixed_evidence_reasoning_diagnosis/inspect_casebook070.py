"""Print a compact, offline human-review view of all 14 full casebooks."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "outputs/070_fixed_evidence_reasoning_diagnosis/casebook_full.jsonl"
for line in path.open(encoding="utf-8"):
    row = json.loads(line)
    print("\nCASE", row["id"][:8], "patient", row["sid"], "author", row["author"], "GT", row["GT"])
    print("CLAIM", row["claim"])
    print("LABELS", row["labels"], "CANDIDATES", row["correct_candidates"])
    print("SCORES", row["scores"])
    chunks = re.split(r"(?=\n\d+\. Date:)", row["reference"])
    ref = {}
    for chunk in chunks:
        match = re.match(r"\n?(\d+)\. Date:", chunk)
        if match:
            ref[int(match.group(1))] = chunk.strip()
    for name in ("NS_U0", "TS_raw", "Qwen_U0"):
        obj = row["outputs"][name]["output"]
        cited = sorted({int(i) for check in obj.get("checks", []) if isinstance(check, dict)
                        for i in check.get("evidence_ids", []) if isinstance(i, int)})
        print(name, "native", obj.get("verdict"), "reason", obj.get("reason"), "cited", cited)
        for check in obj.get("checks", []):
            if check.get("aspect") in ("opposing_case", "overall_assessment"):
                print(" ", check.get("aspect"), check.get("assessment"), check.get("evidence_ids"))
        for i in cited[:5]:
            text = ref.get(i, "MISSING").replace("\n", " ")
            print("  REF", i, text[:480])
