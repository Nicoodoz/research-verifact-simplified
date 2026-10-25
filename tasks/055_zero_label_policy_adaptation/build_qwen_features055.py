from pathlib import Path
import sys,json,csv
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/055_zero_label_policy_adaptation"
sys.path.insert(0,str(ROOT/"tasks/055_zero_label_policy_adaptation"));import run_qwen_full055
sys.path.insert(0,str(ROOT/"tasks/052_first_tier_validation"));import run052,common052 as c52
sys.path.insert(0,str(ROOT/"tasks/053_thinking_prior_validation"));import run053,common053 as c53
VALID=c53.VALID
def lines(p):return [json.loads(s) for s in Path(p).read_text(encoding="utf-8-sig").splitlines() if s.strip()]
def main():
    _,newterm=run_qwen_full055.state()
    new_by_id={t["job"]["id"]:t["parsed"] for t in newterm.values()}
    _,t52=run052.state();_,t53=run053.state()
    old={}
    for t in list(t52.values())+list(t53.values()):
        p=t.get("parsed",{});j=t.get("job",{})
        if str(j.get("request_id","")).startswith(("052_Q_","053_Q_")) and p.get("status") in VALID and p.get("scores") is not None:
            old[(j.get("id"),j.get("request_id"))]=p
    reuse=lines(OUT/"qwen_full_reuse.jsonl")
    reuse_by_id={}
    for r in reuse:
        p=old.get((r["id"],r["existing_request_id"]))
        if p is None:raise RuntimeError("missing reuse "+r["id"])
        reuse_by_id[r["id"]]=p
    assert len(new_by_id)==429,(len(new_by_id),"new")
    assert len(reuse_by_id)==51,(len(reuse_by_id),"reuse")
    allq={**new_by_id,**reuse_by_id};assert len(allq)==480
    rows=[];stats={}
    for pool in ("052","053"):
        feats=lines(OUT/f"features_{pool}.jsonl");n=0
        for r in feats:
            q=allq.get(r["id"])
            if q is None:raise RuntimeError("missing q "+pool+" "+r["id"])
            if q.get("status") not in VALID or q.get("scores") is None:raise RuntimeError("bad q "+r["id"])
            x=dict(r);x["qwen_scores"]=q["scores"];x["qwen_verdict"]=q.get("verdict");rows.append(x);n+=1
        stats[pool]=n
        with (OUT/f"features_qwen_{pool}.jsonl").open("w",encoding="utf-8",newline="\n") as f:
            for x in [z for z in rows if z.get("pool",pool)==pool]:
                pass
        # rewrite explicitly from pool records
        pp=[x for x in rows[-n:]]
        with (OUT/f"features_qwen_{pool}.jsonl").open("w",encoding="utf-8",newline="\n") as f:
            for x in pp:f.write(json.dumps(x,ensure_ascii=False,sort_keys=True)+"\n")
    # Summary raw qwen label performance on valid T-S pools.
    labs=("Supported","Not Supported","Not Addressed")
    out=[]
    for pool in ("052","053"):
        rr=lines(OUT/f"features_qwen_{pool}.jsonl")
        for mode in ("raw","u0","u2"):
            pred=[];gt=[]
            for r in rr:
                sc=r["qwen_scores"]
                if mode=="raw":p=r["qwen_verdict"]
                elif mode=="u0":p=c53.decision(sc,0)
                else:p=c53.decision(sc,2)
                pred.append(p);gt.append(r["GT"])
            correct=sum(a==b for a,b in zip(gt,pred));fs=sum(a!="Supported" and b=="Supported" for a,b in zip(gt,pred))
            rec={k:sum(a==b==k for a,b in zip(gt,pred))/sum(a==k for a in gt) for k in labs}
            out.append(dict(pool=pool,mode=mode,n=len(gt),correct=correct,PA=correct/len(gt),falseS=fs,**{"recall_"+k.replace(" ","_"):v for k,v in rec.items()}))
    with (OUT/"qwen_full_raw_summary.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
    print(json.dumps(dict(stats=stats,new=len(new_by_id),reuse=len(reuse_by_id),summary=out),ensure_ascii=False,indent=2))
if __name__=="__main__":main()
