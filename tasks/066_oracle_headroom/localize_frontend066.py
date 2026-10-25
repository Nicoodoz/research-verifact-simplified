import csv,json,re
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(r"D:\Research-VeriFact")
OUT=ROOT/"outputs/066_oracle_headroom"
cases={x["id"]:x for x in (json.loads(l) for l in open(OUT/"error_cases.jsonl",encoding="utf-8-sig") if l.strip())}
maps={x["id"]:x for x in (json.loads(l) for l in open(OUT/"final_mapping.jsonl",encoding="utf-8-sig") if l.strip())}
res={x["id"]:x for x in csv.DictReader(open(OUT/"evidence_cases.csv",encoding="utf-8"))}
paths={
"031":ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl",
"020":ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl",
"016":ROOT/"outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl",
"009":ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl"}
corpora={}
for name,p in paths.items():
 corpora[name]={x["passage_id"]:x for x in (json.loads(l) for l in open(p,encoding="utf-8-sig") if l.strip())}
def norm(s):return re.sub(r"\s+"," ",s).strip().lower()
cnt=Counter();rows=[]
for pid,r in res.items():
 if r["evidence_fix"]!="True":continue
 x=cases[pid];m=maps[pid];cor=corpora[x["corpus_source"]];base=norm(x["baseline_reference"])
 kept=m["kept_pids"];inbase=[]
 for z in kept:
  text=norm(cor[z]["text"]) if z in cor else ""
  inbase.append(bool(text and text in base))
 c48=set(x.get("c48_pids",[]))
 if kept and all(inbase):
  cat="already_in_final_reference_recomposition"
 elif c48 and all(z in c48 for z in kept):
  cat="C48_to_final_pack_selection"
 elif c48:
  cat="retrieval_or_mixed"
 else:
  cat="upstream_unlocalized"
 cnt[cat]+=1
 rows.append((pid,x["GT"],cat,len(kept),sum(inbase)))
print(cnt)
for z in rows:print(z)
