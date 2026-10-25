"""Zero-API summary of 082's already frozen 24 same-body repeats."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
source = ROOT / "outputs/082_anchor_configuration_adaptation/repeat_predictions.jsonl"
out = ROOT / "outputs/084_f4_coverage_validation/historical_repeat_sensitivity.json"
rows = [json.loads(s) for s in source.open(encoding="utf-8-sig") if s.strip()]
assert len(rows) == 24 and len({x["sid"] for x in rows}) == 22
summary = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
           "scope": "082 historical old352 subset, not an 084 new repeat", "n": len(rows),
           "patients": len({x["sid"] for x in rows}), "arms": {}}
for arm in ("B", "F4"):
    first = [x["original_methods"][arm]["PriorG"] for x in rows]
    repeat = [x["methods"][arm]["PriorG"] for x in rows]
    summary["arms"][arm] = {"first_correct": sum(p == x["GT"] for x,p in zip(rows,first)),
                            "repeat_correct": sum(p == x["GT"] for x,p in zip(rows,repeat)),
                            "label_flips": sum(a != b for a,b in zip(first,repeat)),
                            "first_false_S": sum(x["GT"] != "Supported" and p == "Supported" for x,p in zip(rows,first)),
                            "repeat_false_S": sum(x["GT"] != "Supported" and p == "Supported" for x,p in zip(rows,repeat))}
summary["F4_minus_B_net_correct_first"] = summary["arms"]["F4"]["first_correct"]-summary["arms"]["B"]["first_correct"]
summary["F4_minus_B_net_correct_repeat"] = summary["arms"]["F4"]["repeat_correct"]-summary["arms"]["B"]["repeat_correct"]
out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8",newline="\n")
print(json.dumps(summary,ensure_ascii=False))
