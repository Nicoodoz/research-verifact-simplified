"""Read complete packets from any frozen review version."""
import argparse
from pathlib import Path
import study009 as s

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("packets",type=Path)
    ap.add_argument("cases",nargs="+")
    args=ap.parse_args()
    for pack in s.pilot.jsonl(args.packets):
        r=pack["row"]
        if r["case_id"] not in args.cases:
            continue
        print("\nCASE",r["case_id"],r["author_type"],"GT",r["human_gt"],{a:r[a] for a in ("A48","B48","C48")})
        print("CLAIM:",pack["input"]["text"])
        for key,p in sorted(pack["passages"].items(),key=lambda kv:(kv[1]["date"],kv[1]["time"],kv[1]["note_id"],kv[1]["start"])):
            members={a:pack["input"]["retrieval"][a]["selected_ids"].index(key)+1 for a in ("A48","B48","C48") if key in pack["input"]["retrieval"][a]["selected_ids"]}
            print("EHR",p["note_id"],p["date"],p["time"],"OFFSET",p["start"],p["end_exclusive"],"REF",members,"ID",key)
            print(p["text"])
        seen={}
        for a in ("A48","B48","C48"):
            result=pack["outputs"][a]
            if result["request_id"] in seen:
                print("JUDGE",a,"same result as",seen[result["request_id"]])
            else:
                print("FULL JUDGE",a,result.get("output_text"))
                seen[result["request_id"]]=a
