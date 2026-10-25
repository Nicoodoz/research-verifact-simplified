"""Display complete frozen 006 review material with repeated JSON formatting removed."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "outputs/006_source_context_feasibility/run_001/review_001"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--cases", nargs="*", default=[])
parser.add_argument("--patient")
parser.add_argument("--start", type=int, default=0)
parser.add_argument("--count", type=int, default=100)
args = parser.parse_args()
if args.patient:
    blocks = json.loads((ROOT / "reference_unions" / (args.patient + ".json")).read_text(encoding="utf-8"))
    last = None
    for i in range(args.start, min(args.start + args.count, len(blocks))):
        header, separator, body = blocks[i]["text"].partition(" | Text: ")
        assert separator
        if header != last:
            print("\n" + header)
            last = header
        print(f"[{i}] " + body)
    print(f"END [{args.start},{min(args.start+args.count,len(blocks))}) of {len(blocks)}")
else:
    for cid in args.cases:
        packet = json.loads((ROOT / "packets" / (cid + ".json")).read_text(encoding="utf-8"))
        print("\n" + cid + " GT=" + packet["case"]["human_gt"] + " " + packet["case"]["primary_outcome"])
        print("CLAIM: " + packet["input"]["text"])
        print("SOURCE: " + packet["input"]["source_context"]["text"])
        for arm, response in packet["responses"].items():
            print("\n" + arm)
            if not response:
                print("NO RECEIVED RESPONSE")
                continue
            raw = response.get("output_text") or ""
            try:
                answer = json.loads(raw)
            except ValueError:
                print(raw)
                continue
            assert set(answer) == {"verdict", "reason", "checks"}
            print("VERDICT: " + answer["verdict"] + "\nREASON: " + answer["reason"])
            for check in answer["checks"]:
                print(json.dumps(check, ensure_ascii=False))
