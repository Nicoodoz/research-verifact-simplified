"""Display selected pages from downloaded primary paper text."""
import argparse
import json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument("paper")
p.add_argument("pages",nargs="+",type=int)
a=p.parse_args()
root=Path(__file__).resolve().parents[2]/"docs/sources/008_retrieval_planning"
pages=json.loads((root/(a.paper+"_pages.json")).read_text(encoding="utf-8"))
for number in a.pages:
    print(f"\n=== {a.paper} PAGE {number} ===\n"+pages[number-1]["text"])
