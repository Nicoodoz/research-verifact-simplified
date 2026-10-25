import json,collections
from pathlib import Path
ROOT=Path(r"D:\Research-VeriFact")
A=ROOT/"outputs/067_conservative_evidence_packing/attempts"
cnt=collections.Counter();pref=collections.Counter();uids=set();dup=0;total=0
for p in sorted(A.glob("*/request.json")):
 x=json.load(open(p,encoding="utf-8"));j=x["job"];rid=j["request_id"];total+=1
 cnt[j.get("stage")]+=1
 pref[rid.split("_")[1] if "_" in rid else rid]+=1
 if rid in uids:dup+=1
 uids.add(rid)
print("attempt dirs",total,"unique request ids",len(uids),"dup ids",dup)
print("stages",cnt)
print("prefix",pref)
print("expected current stage1",sum(1 for _ in open(ROOT/"outputs/067_conservative_evidence_packing/stage1_jobs.jsonl",encoding="utf-8")))
print("expected current stage2",sum(1 for _ in open(ROOT/"outputs/067_conservative_evidence_packing/stage2_jobs.jsonl",encoding="utf-8")))
