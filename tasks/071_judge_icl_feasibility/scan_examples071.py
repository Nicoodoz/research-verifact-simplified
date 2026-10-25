"""Offline ranked reading list; ranking never uses Judge outcome or eval labels."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = [json.loads(s) for s in (ROOT / "outputs/053_thinking_prior_validation/evaluation_cases.jsonl").read_text(encoding="utf-8").splitlines()]
patients = sorted({x["sid"] for x in rows}, key=lambda v: hashlib.sha256(("071/eval/v1:" + v).encode()).hexdigest())
train = set(patients[16:])
cohort = {r["proposition_id"]: r for r in csv.DictReader((ROOT / "outputs/002_reproduce_paper_results/run_003/cohort_master.csv").open(encoding="utf-8-sig"))}
stop = {"the", "was", "were", "and", "with", "his", "her", "patient", "had", "for", "after", "that", "this", "they", "from", "there", "which", "during", "into"}


def words(s):
    return {w for w in re.findall(r"[a-zA-Z0-9]+", s.lower()) if len(w) >= 3 and w not in stop}


out = []
for x in rows:
    c = cohort[x["id"]]
    if x["sid"] not in train or c["initial_agreement"] != "3" or c["second_round_anomaly"] != "False":
        continue
    claim_words = words(x["claim"])
    blocks = re.split(r"(?=\n\d+\. Date:)", x["reference"])
    match = max(blocks, key=lambda b: len(claim_words & words(b)))
    score = len(claim_words & words(match)) / max(len(claim_words), 1)
    out.append((score, x, match))
for score, x, match in sorted(out, key=lambda v: (-v[0], v[1]["id"])):
    if x["GT"] != "Supported":
        continue
    print(f'{score:.2f}', x["id"][:8], x["sid"], x["claim"])
    print(" ", match.replace("\n", " ")[:380])
    if sum(z[1]["GT"] == "Supported" for z in out if z[0] > score) >= 25:
        break
