from pathlib import Path
import csv,importlib.util,numpy as np
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"tasks/064_safe_policy_selection/run064_future_v2.py"
s=importlib.util.spec_from_file_location("fv2",P);fv2=importlib.util.module_from_spec(s);s.loader.exec_module(fv2)
r=fv2.r; LABS=r.LABS
def predmap(task):
 rows=list(csv.DictReader(open(ROOT/f"outputs/{task}/predictions.csv",encoding="utf-8-sig")))
 return {x["id"]:x for x in rows}
PM={"052":predmap("052_first_tier_validation"),"053":predmap("053_thinking_prior_validation")}
RR=list(csv.DictReader(open(ROOT/"outputs/064_safe_policy_selection/future_v2_replicate_results.csv",encoding="utf-8-sig")))
def avg(src,tgt,b=10):
 pool=r.load_pool(tgt,True); srcpool=r.load_pool(src,True); shapes=r.source_shapes(srcpool)
 sel={(int(x["rep"])):x["selected_policy"] for x in RR if x["source"]==src and x["target"]==tgt and x["strategy"]=="active_policy" and int(x["budget"])==b}
 vals={m:[] for m in ("U2","GateA","FrozenPriorG","064_active10")}
 for rep in range(50):
  cal,fut,_,_=fv2.split_patients(pool,src,tgt,rep)
  ids=[x["id"] for x in fut]
  methods={
   "U2":[PM[tgt][i]["U2"] for i in ids],
   "GateA":[PM[tgt][i]["GateA" if tgt=="053" else "GateA_patient_out"] for i in ids],
   "FrozenPriorG":[LABS[x["ds"]] for x in fut],
   "064_active10":[LABS[z] for z in r.policy_predict(fut,sel[rep])]
  }
  for m,preds in methods.items():
   pp=np.array([LABS.index(x) for x in preds],int); met=r.r063.metrics(fut,pp); vals[m].append(met)
 for m,A in vals.items():
  print(src+"->"+tgt,m,{k:round(float(np.mean([x[k] for x in A])),6) for k in ("PA","MCC","falseS_rate","S","NS","NA")})
for pair in (("052","053"),("053","052")): avg(*pair)
