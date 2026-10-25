"""Future GT-blind materialization of all 360 frozen R1 raw endpoint receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from parse_r1 import ParserProfile, parse

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/085_r1_70b_model_swap"


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def lines(path): return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s]


def main():
    p=argparse.ArgumentParser(description="Parse future raw R1 receipts without opening GT")
    p.add_argument("--receipt-index",type=Path,required=True,help="JSONL: id, sid, arm, raw_response_path, model_verified")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    frozen_path=OUT/"deferred_preflight/parser_profile_frozen.json"
    profile_json=json.loads(frozen_path.read_text(encoding="utf-8"))
    profile=ParserProfile.from_json(profile_json)
    profile_sha=sha(frozen_path)
    jobs=lines(OUT/"neutral_jobs.jsonl")
    expected={(j["id"],j["arm"]):j["sid"] for j in jobs}
    assert len(expected)==360
    index=lines(args.receipt_index)
    keyed={(x["id"],x["arm"]):x for x in index}
    if len(keyed)!=360 or set(keyed)!=set(expected):
        raise ValueError("Receipt index must contain all 360 frozen ID/arm pairs exactly once")
    rows=[]
    for job in jobs:
        x=keyed[job["id"],job["arm"]]
        if x["sid"]!=expected[job["id"],job["arm"]]: raise ValueError("Patient mismatch")
        if x.get("model_verified") is not True: raise ValueError("Endpoint model identity not verified")
        raw_path=ROOT/x["raw_response_path"]
        if not raw_path.is_file(): raise FileNotFoundError(raw_path)
        parsed=parse(raw_path.read_bytes(),profile)
        rows.append({"id":job["id"],"sid":job["sid"],"arm":job["arm"],
                     "raw_response_path":x["raw_response_path"],"raw_response_sha256":sha(raw_path),
                     "parser_profile_sha256":profile_sha,**parsed})
    with args.output.open("x",encoding="utf-8",newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
    print(json.dumps({"materialized":len(rows),"valid":sum(x["valid"] for x in rows),
                      "invalid":sum(not x["valid"] for x in rows)},ensure_ascii=False))


if __name__=="__main__": main()
