from pathlib import Path
import importlib.util, collections
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"tasks/064_safe_policy_selection/run064.py"
s=importlib.util.spec_from_file_location("r",P)
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
for tag in ("052","053"):
    rows=r.load_pool(tag,True)
    rr=[x for x in rows if x["policy_preds"][0]!=0 and x["policy_preds"][3]==0]
    print(tag,"R90 region",len(rr),"claims",len(set(x["sid"] for x in rr)),"patients")
    c=collections.Counter(x["sid"] for x in rr)
    print(c)
    print("GT",collections.Counter(r.LABS[x["y"]] for x in rr))
