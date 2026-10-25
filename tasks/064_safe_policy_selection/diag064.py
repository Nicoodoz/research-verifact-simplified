import csv,json,collections
P="outputs/064_safe_policy_selection/replicate_results.csv"
R=list(csv.DictReader(open(P,encoding="utf-8")))
X=[r for r in R if r["source"]=="052" and r["target"]=="053" and r["strategy"]=="active_policy" and r["budget"]=="5"]
allc=collections.Counter(); selc=collections.Counter()
nsel=sum(r["selected_policy"]=="R90" for r in X)
for r in X:
    d=json.loads(r["label_sig_counts"]); allc.update(d)
    if r["selected_policy"]=="R90": selc.update(d)
print("n",len(X),"R90",nsel)
print("all_avg",{k:round(v/len(X),2) for k,v in allc.items()})
print("R90_avg",{k:round(v/max(1,nsel),2) for k,v in selc.items()})
