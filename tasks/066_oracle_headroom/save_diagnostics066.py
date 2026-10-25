import csv,json,re,sys
from pathlib import Path
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/066_oracle_headroom"
sys.path.insert(0,str(ROOT/"tasks/066_oracle_headroom"))
import common066 as c,run066
cases={x["id"]:x for x in c.lines(OUT/"error_cases.jsonl")}
maps={x["id"]:x for x in c.lines(OUT/"final_mapping.jsonl")}
ev={r["id"]:r for r in csv.DictReader(open(OUT/"evidence_cases.csv",encoding="utf-8"))}
paths={"031":ROOT/"outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl","020":ROOT/"outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl","016":ROOT/"outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl","009":ROOT/"outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl"}
corpora={n:{x["passage_id"]:x for x in c.lines(p)} for n,p in paths.items()}
def norm(s):return re.sub(r"\s+"," ",s).strip().lower()
loc=Counter();detail=[]
for pid,r in ev.items():
 if r["evidence_fix"]!="True":continue
 x=cases[pid];m=maps[pid];cor=corpora[x["corpus_source"]];base=norm(x["baseline_reference"])
 kept=m["kept_pids"];inbase=[bool(z in cor and norm(cor[z]["text"]) in base) for z in kept];c48=set(x.get("c48_pids",[]))
 if kept and all(inbase):cat="already_in_final_reference_recomposition"
 elif c48 and all(z in c48 for z in kept):cat="C48_to_final_pack_selection"
 elif c48:cat="retrieval_or_mixed"
 else:cat="upstream_unlocalized"
 loc[cat]+=1;detail.append({"id":pid,"GT":x["GT"],"category":cat,"kept_n":len(kept),"already_in_baseline_n":sum(inbase)})
pred=list(csv.DictReader(open(ROOT/"outputs/053_thinking_prior_validation/predictions.csv",encoding="utf-8-sig")));byid={r["id"]:r for r in pred};errors={r["id"] for r in pred if r["TS_PriorG"]!=r["GT"]}
qrows={x["id"]:x for x in c.lines(ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl")}
_,term=run066.state();reasonfix={}
for r in pred:
 cand=[r["TS_PriorG"]]
 if r.get("NS_U0") in c.LABELS:cand.append(r["NS_U0"])
 if r.get("TS_status")=="valid" and r.get("TS_raw") in c.LABELS:cand.append(r["TS_raw"])
 if r["id"] in qrows:
  q=qrows[r["id"]]["qwen_scores"];cand.append(max(c.LABELS,key=lambda k:float(q[k])))
 reasonfix[r["id"]]=r["GT"] in cand
rawfix=pgfix=raw_only=pg_only=0;neither=Counter();neither_gt=Counter()
for pid in errors:
 m=maps[pid];rid=m.get("judge_request_id");raw=pg=None
 if rid and rid in term:
  z=term[rid]["parsed"]
  if z.get("status") in ("valid","valid_with_format_anomaly") and z.get("verdict") in c.LABELS and z.get("scores"):
   raw=z["verdict"];pg=c.priorg(z["scores"])
 rf=raw==byid[pid]["GT"];pf=pg==byid[pid]["GT"]
 rawfix+=rf;pgfix+=pf;raw_only+=rf and not pf;pg_only+=pf and not rf
 if not reasonfix[pid] and not pf:
  key=("decisive" if bool(m.get("composer_decisive")) else "nondecisive")+("_judge" if rid and rid in term else "_nojudge")
  neither[key]+=1;neither_gt[byid[pid]["GT"]]+=1
out={"frontend_localization":dict(loc),"frontend_details":detail,"evidence_raw_fix":rawfix,"evidence_priorg_fix":pgfix,"raw_only_fix":raw_only,"priorg_only_fix":pg_only,"neither_diagnostic":dict(neither),"neither_gt":dict(neither_gt)}
(OUT/"diagnostics_001.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(out,ensure_ascii=False,indent=2))
