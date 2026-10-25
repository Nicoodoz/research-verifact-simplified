"""Page through complete selected reference unions without repeated note headers."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("patient")
parser.add_argument("start", type=int)
parser.add_argument("stop", type=int)
args = parser.parse_args()
path = ROOT / "outputs/005_pilot_effect_analysis/run_002/reference_unions" / (args.patient + ".json")
blocks = json.loads(path.read_text(encoding="utf-8"))
print(f"PATIENT {args.patient} BLOCKS [{args.start}, {min(args.stop,len(blocks))}) OF {len(blocks)}")
last = None
for index in range(args.start, min(args.stop, len(blocks))):
    row = blocks[index]
    header, separator, body = row["text"].partition(" | Text: ")
    assert separator
    if header != last:
        print("\n" + header)
        last = header
    print(f"[{index}] " + ",".join(f"{o['case']}:{o['number']}" for o in row["occurrences"]) + " | " + body)
