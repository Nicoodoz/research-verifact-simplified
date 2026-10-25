from pathlib import Path
import csv, hashlib, importlib.util, json, math, subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/064_safe_policy_selection"
O055=ROOT/"outputs/055_zero_label_policy_adaptation"
P063=ROOT/"tasks/063_minimal_label_reliability/run063.py"

spec=importlib.util.spec_from_file_location("r063",P063)
r063=importlib.util.module_from_spec(spec);spec.loader.exec_module(r063)

LABS=r063.LABS
POLICIES=("BASE","V80","V60","R90","C80","C60")
BUDGETS=(0,3,5,10,20)
REPS=50
MC=2000
SEED=20260923064
SOURCE_STRENGTH=1.0
RISK_MAX=.25
P_GAIN_MIN=.80

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_jsonl(p):
    with Path(p).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]

def csvwrite(p,rows):
    rows=list(rows)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def put(p,obj):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def load_pool(tag,include_gt=True):
    base=r063.load_pool(tag,include_gt)
    raw=read_jsonl(O055/f"features_qwen_{tag}.jsonl")
    out=[]
    for b,x in zip(base,raw):
        qv=np.array([float(x["qwen_scores"][k]) for k in LABS],float)
        z=dict(b);z["q"]=int(np.argmax(qv));z["qtop"]=float(qv.max());z["qS"]=float(qv[0])
        z["policy_preds"]=policy_preds(z)
        z["signature"]=tuple(z["policy_preds"])
        out.append(z)
    return out
def policy_preds(x):
    b=int(x["ds"]);q=int(x["q"]);qt=float(x["qtop"]);qs=float(x["qS"])
    v80=q if b==0 and q!=0 and qt>=80 else b
    v60=q if b==0 and q!=0 and qt>=60 else b
    r90=0 if b!=0 and q==0 and qs>=90 else b
    c80=q if r90==0 and q!=0 and qt>=80 else r90
    c60=q if r90==0 and q!=0 and qt>=60 else r90
    return (b,v80,v60,r90,c80,c60)

def sigkey(sig): return "-".join(str(int(x)) for x in sig)

def source_shapes(rows):
    counts={}
    for r in rows:
        k=r["signature"]
        if k not in counts: counts[k]=np.full(3,.5,float)
        counts[k][r["y"]]+=1
    return {k:v/v.sum() for k,v in counts.items()}

def target_sig_counts(rows):
    out={}
    for r in rows: out[r["signature"]]=out.get(r["signature"],0)+1
    return out
def posterior_alpha(sig,shapes,label_counts):
    shape=shapes.get(sig,np.full(3,1/3))
    return SOURCE_STRENGTH*np.asarray(shape,float)+np.asarray(label_counts.get(sig,np.zeros(3)),float)

def normal_cdf(z):
    return .5*(1+math.erf(float(z)/math.sqrt(2)))

def gain_prob(alpha,alt,base):
    a=np.asarray(alpha,float);A=float(a.sum())
    m=a/A
    md=float(m[alt]-m[base])
    vi=a[alt]*(A-a[alt])/(A*A*(A+1))
    vj=a[base]*(A-a[base])/(A*A*(A+1))
    cij=-a[alt]*a[base]/(A*A*(A+1))
    sd=math.sqrt(max(float(vi+vj-2*cij),1e-12))
    return normal_cdf(md/sd),md

def posterior_samples(shapes,label_counts,target_counts,remaining_counts,rng):
    return {
        sig:rng.dirichlet(posterior_alpha(sig,shapes,label_counts),size=MC)
        for sig in target_counts if remaining_counts.get(sig,0)>0
    }
def policy_posterior(shapes,label_counts,target_counts,remaining_counts,rng):
    samp=posterior_samples(shapes,label_counts,target_counts,remaining_counts,rng)
    out={}
    for j,name in enumerate(POLICIES):
        if j==0:
            out[name]={"certified":True,"mean_gain":0.0,"p_gain":1.0,
                       "rescue_risk":0.0,"veto_harm":0.0,"changes":0}
            continue
        dg=np.zeros(MC,float);rb=np.zeros(MC,float);vb=np.zeros(MC,float)
        rn=0;vn=0;changes=0
        for sig,P in samp.items():
            n=int(remaining_counts.get(sig,0))
            b=int(sig[0]);a=int(sig[j])
            if n<=0 or a==b: continue
            changes+=n;dg+=n*(P[:,a]-P[:,b])
            if a==0 and b!=0:
                rn+=n;rb+=n*(1-P[:,0])
            if b==0 and a!=0:
                vn+=n;vb+=n*P[:,0]
        mean_gain=float(dg.mean()) if changes else 0.0
        pg=float(np.mean(dg>0)) if changes else 0.0
        rr=float(rb.mean()/rn) if rn else 0.0
        vh=float(vb.mean()/vn) if vn else 0.0
        cert=bool(changes and mean_gain>0 and pg>=P_GAIN_MIN and
                  (rn==0 or rr<=RISK_MAX) and (vn==0 or vh<=RISK_MAX))
        out[name]={"certified":cert,"mean_gain":mean_gain,"p_gain":pg,
                   "rescue_risk":rr,"veto_harm":vh,"changes":changes}
    return out
def select_policy(shapes,label_counts,target_counts,remaining_counts,rng):
    post=policy_posterior(shapes,label_counts,target_counts,remaining_counts,rng)
    cand=[(v["mean_gain"],-v["changes"],name) for name,v in post.items()
          if name!="BASE" and v["certified"]]
    if not cand:return "BASE",post
    cand.sort(reverse=True)
    return cand[0][2],post

def decision_uncertainty(sig,alpha,remaining_n):
    if remaining_n<=0 or len(set(sig))<=1:return -1.0
    b=int(sig[0]);alts=sorted(set(sig[1:])-{b})
    best=0.0
    m=np.asarray(alpha,float)/np.sum(alpha)
    for a in alts:
        pg,_=gain_prob(alpha,a,b)
        u=4*pg*(1-pg)
        if a==0 and b!=0:risk=1-float(m[0]);u+=math.exp(-abs(risk-RISK_MAX)/.15)
        elif b==0 and a!=0:risk=float(m[0]);u+=math.exp(-abs(risk-RISK_MAX)/.15)
        best=max(best,u)
    return float(remaining_n*best)
def active_select_indices(rows,budget,shapes,rng):
    selected=[];used_sid=set();label_counts={};sig_selected={}
    target_counts=target_sig_counts(rows)
    disagree=[s for s in target_counts if len(set(s))>1]

    for step in range(min(budget,len(rows))):
        remaining_counts={
            s:target_counts[s]-sig_selected.get(s,0) for s in target_counts
        }
        uncovered=[s for s in disagree if sig_selected.get(s,0)==0 and remaining_counts[s]>0]
        if uncovered:
            maxn=max(remaining_counts[s] for s in uncovered)
            cand_s=[s for s in uncovered if remaining_counts[s]==maxn]
            sig=cand_s[int(rng.integers(len(cand_s)))]
        else:
            scored=[]
            for s in disagree:
                a=posterior_alpha(s,shapes,label_counts)
                sc=decision_uncertainty(s,a,remaining_counts.get(s,0))
                scored.append((sc,s))
            scored=[x for x in scored if x[0]>=0]
            if not scored:break
            mx=max(x[0] for x in scored)
            cand_s=[s for sc,s in scored if abs(sc-mx)<1e-12]
            sig=cand_s[int(rng.integers(len(cand_s)))]

        cand=[i for i,r in enumerate(rows) if r["signature"]==sig and i not in selected]
        unseen=[i for i in cand if rows[i]["sid"] not in used_sid]
        use=unseen if unseen else cand
        if not use:break
        i=use[int(rng.integers(len(use)))]
        selected.append(i);used_sid.add(rows[i]["sid"])
        sig_selected[sig]=sig_selected.get(sig,0)+1
        # GT is revealed only after selection.
        if "y" in rows[i]:
            label_counts.setdefault(sig,np.zeros(3,int))[rows[i]["y"]]+=1
    return selected
def random_global_indices(rows,budget,rng):
    return r063.select_random(rows,budget,rng)

def label_counts_from(rows,idx):
    out={}
    for i in idx:
        r=rows[i];out.setdefault(r["signature"],np.zeros(3,int))[r["y"]]+=1
    return out

def remaining_sig_counts(rows,idx):
    total=target_sig_counts(rows);sel={}
    for i in idx:
        s=rows[i]["signature"];sel[s]=sel.get(s,0)+1
    return {s:total[s]-sel.get(s,0) for s in total}

def policy_index(name): return POLICIES.index(name)

def policy_predict(rows,name):
    j=policy_index(name)
    return np.array([r["policy_preds"][j] for r in rows],int)
def true_policy_safety(rows,name):
    base=policy_predict(rows,"BASE");pred=policy_predict(rows,name)
    y=np.array([r["y"] for r in rows],int)
    changed=pred!=base
    gain=int(np.sum(pred==y)-np.sum(base==y))
    rescue=(changed)&(base!=0)&(pred==0)
    veto=(changed)&(base==0)&(pred!=0)
    rr=float(np.mean(y[rescue]!=0)) if np.any(rescue) else 0.0
    vh=float(np.mean(y[veto]==0)) if np.any(veto) else 0.0
    m=r063.metrics(rows,pred);b=r063.metrics(rows,base)
    safe=bool(gain>0 and
              (not np.any(rescue) or rr<=RISK_MAX) and
              (not np.any(veto) or vh<=RISK_MAX) and
              m["NS"]>=b["NS"]-.02-1e-12 and
              m["NA"]>=b["NA"]-.02-1e-12)
    return {"gain":gain,"rescue_risk":rr,"veto_harm":vh,
            "safe":safe,"metrics":m,"base_metrics":b}
def oracle_info(rows):
    info={name:true_policy_safety(rows,name) for name in POLICIES}
    safe=[name for name in POLICIES[1:] if info[name]["safe"]]
    if not safe:return "BASE",{"BASE"},info
    safe_sorted=sorted(safe,key=lambda n:(info[n]["metrics"]["MCC"],
                                         info[n]["metrics"]["PA"],
                                         info[n]["gain"]),reverse=True)
    best=safe_sorted[0]
    return best,set(safe),info
def seeded_rng(source,target,strategy,budget,rep,suffix=""):
    s=f"{SEED}:{source}:{target}:{strategy}:{budget}:{rep}:{suffix}"
    h=hashlib.sha256(s.encode()).hexdigest()
    return np.random.default_rng(int(h[:16],16))

def one_run(source,target,source_rows,target_rows,strategy,budget,rep,
            shapes,oracle_name,safe_set):
    arng=seeded_rng(source,target,strategy,budget,rep,"acquire")
    if budget==0:
        idx=[]
    elif strategy=="random_global":
        idx=random_global_indices(target_rows,budget,arng)
    elif strategy=="active_policy":
        idx=active_select_indices(target_rows,budget,shapes,arng)
    else:
        raise ValueError(strategy)

    lc=label_counts_from(target_rows,idx)
    rem=remaining_sig_counts(target_rows,idx)
    tcounts=target_sig_counts(target_rows)
    mrng=seeded_rng(source,target,strategy,budget,rep,"mc")
    selected,post=select_policy(shapes,lc,tcounts,rem,mrng)

    sel=set(idx);hold=[r for i,r in enumerate(target_rows) if i not in sel]
    pp=policy_predict(hold,selected);bp=policy_predict(hold,"BASE")
    pm=r063.metrics(hold,pp);bm=r063.metrics(hold,bp)
    fullp=policy_predict(target_rows,selected)
    for i in idx: fullp[i]=target_rows[i]["y"]
    om=r063.metrics(target_rows,fullp)
    ylab=np.array([target_rows[i]["y"] for i in idx],int) if idx else np.array([],int)
    lclass=np.bincount(ylab,minlength=3) if len(ylab) else np.zeros(3,int)
    chosen=post[selected]

    row={
        "source":source,"target":target,"strategy":strategy,
        "budget":budget,"rep":rep,"selected_policy":selected,
        "oracle_policy":oracle_name,
        "oracle_match":selected==oracle_name,
        "selected_safe_full":selected=="BASE" or selected in safe_set,
        "unsafe_switch":selected!="BASE" and selected not in safe_set,
        "beneficial_nonbase_select":selected!="BASE" and selected in safe_set,
        "base_fallback":selected=="BASE",
        "labeled_S":int(lclass[0]),"labeled_NS":int(lclass[1]),"labeled_NA":int(lclass[2]),
        "labeled_disagreement":int(sum(len(set(target_rows[i]["signature"]))>1 for i in idx)),
        "label_sig_counts":json.dumps({sigkey(k):int(v.sum()) for k,v in lc.items()},sort_keys=True),
        "post_mean_gain":chosen["mean_gain"],"post_p_gain":chosen["p_gain"],
        "post_rescue_risk":chosen["rescue_risk"],"post_veto_harm":chosen["veto_harm"],
    }
    for pref,m in (("policy",pm),("base",bm),("operation",om)):
        for k,v in m.items():row[f"{pref}_{k}"]=v
    for k in ("PA","MCC","falseS_rate","S","NS","NA"):
        row[f"delta_{k}"]=pm[k]-bm[k]
    return row

def meanf(vals):
    a=np.asarray(vals,float);a=a[np.isfinite(a)]
    return float(a.mean()) if len(a) else float("nan")

def summarize(rows):
    out=[]
    keys=sorted(set((r["source"],r["target"],r["strategy"],r["budget"]) for r in rows))
    for key in keys:
        x=[r for r in rows if (r["source"],r["target"],r["strategy"],r["budget"])==key]
        source,target,strategy,budget=key
        z={"source":source,"target":target,"strategy":strategy,"budget":budget,"reps":len(x)}
        for k in ("oracle_match","selected_safe_full","unsafe_switch","beneficial_nonbase_select","base_fallback"):
            z[f"{k}_rate"]=float(np.mean([r[k] for r in x]))
        for k in ("delta_PA","delta_MCC","delta_falseS_rate","delta_S","delta_NS","delta_NA",
                  "labeled_S","labeled_NS","labeled_NA","labeled_disagreement"):
            z[f"mean_{k}"]=meanf([r[k] for r in x])
        pol={}
        for r in x:pol[r["selected_policy"]]=pol.get(r["selected_policy"],0)+1
        z["selected_policy_distribution"]=json.dumps(pol,sort_keys=True)
        z["oracle_policy"]=x[0]["oracle_policy"]
        out.append(z)
    return out

def direction_pass(r):
    common=(r["unsafe_switch_rate"]<=.10 and
            r["mean_delta_PA"]>=-1e-12 and r["mean_delta_MCC"]>=-1e-12 and
            r["mean_delta_NS"]>=-.02-1e-12 and r["mean_delta_NA"]>=-.02-1e-12)
    if not common:return False
    if r["oracle_policy"]=="BASE":
        return r["base_fallback_rate"]>=.90
    return r["beneficial_nonbase_select_rate"]>=.70

def minimum_active_budget(summary):
    for b in BUDGETS[1:]:
        rr=[r for r in summary if r["strategy"]=="active_policy" and r["budget"]==b]
        if len(rr)==2 and all(direction_pass(r) for r in rr):return b
    return None
def freeze():
    inputs={
        "features_qwen_052":O055/"features_qwen_052.jsonl",
        "features_qwen_053":O055/"features_qwen_053.jsonl",
        "run063":P063,
        "protocol":ROOT/"tasks/064_safe_policy_selection/protocol.md",
    }
    obj={
        "git_head":subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"policies":list(POLICIES),"budgets":list(BUDGETS),
        "reps":REPS,"mc":MC,"source_strength":SOURCE_STRENGTH,
        "risk_max":RISK_MAX,"p_gain_min":P_GAIN_MIN,
        "code_sha256":sha(Path(__file__)),
        "inputs":{k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)}
                  for k,v in inputs.items()},
    }
    put(OUT/"freeze.json",obj);return obj

def blind_direction(source,target):
    src=load_pool(source,True)
    tgt=load_pool(target,False)
    shapes=source_shapes(src);tc=target_sig_counts(tgt)
    rem=tc.copy();lc={}
    rng=seeded_rng(source,target,"zero_label",0,0,"mc")
    selected,post=select_policy(shapes,lc,tc,rem,rng)
    changes={}
    for j,name in enumerate(POLICIES):
        changes[name]=int(sum(r["policy_preds"][j]!=r["policy_preds"][0] for r in tgt))
    disagree=int(sum(len(set(r["signature"]))>1 for r in tgt))
    return src,tgt,shapes,{
        "source":source,"target":target,"target_n":len(tgt),
        "signature_counts":json.dumps({sigkey(k):v for k,v in tc.items()},sort_keys=True),
        "disagreement_n":disagree,
        "policy_changes":json.dumps(changes,sort_keys=True),
        "zero_label_selected":selected,
        "zero_label_post":json.dumps(post,sort_keys=True),
    }
def self_test():
    src=load_pool("052",True);tgt=load_pool("053",True);blind=load_pool("053",False)
    assert len(src)==236 and len(tgt)==237
    shapes=source_shapes(src)
    rng=seeded_rng("052","053","active_policy",3,0,"acquire")
    a=active_select_indices(tgt,3,shapes,rng)
    rng=seeded_rng("052","053","active_policy",3,0,"acquire")
    b=active_select_indices(blind,3,shapes,rng)
    assert a==b and len(a)==3
    tc=target_sig_counts(blind)
    sel,post=select_policy(shapes,{},tc,tc.copy(),
                           seeded_rng("052","053","zero_label",0,0,"mc"))
    assert sel in POLICIES and all(np.isfinite(v["mean_gain"]) for v in post.values())
    print("064 SELF-TEST PASS",{
        "first3":a,"zero_label":sel,
        "disagreement":sum(len(set(r["signature"]))>1 for r in blind),
    })

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for n in ("freeze.json","actual_unlabeled.csv","replicate_results.csv"):
        if (OUT/n).exists():raise RuntimeError("formal output exists: "+n)
    fr=freeze()
    blind_rows=[];blind_cache={}
    for source,target in (("052","053"),("053","052")):
        src,tgt,shapes,row=blind_direction(source,target)
        blind_rows.append(row);blind_cache[(source,target)]=(src,tgt,shapes)
    csvwrite(OUT/"actual_unlabeled.csv",blind_rows)
    blind_sha=sha(OUT/"actual_unlabeled.csv")
    # GT unblind only after the blind target-policy structure is frozen.
    true_pools={k:load_pool(k,True) for k in ("052","053")}
    oracle_rows=[];oracle_cache={}
    for source,target in (("052","053"),("053","052")):
        oname,safe,info=oracle_info(true_pools[target])
        oracle_cache[(source,target)]=(oname,safe,info)
        for name in POLICIES:
            z=info[name]
            oracle_rows.append({
                "source":source,"target":target,"policy":name,
                "oracle_selected":name==oname,"oracle_safe":name in safe,
                "correct_gain":z["gain"],"rescue_risk":z["rescue_risk"],
                "veto_harm":z["veto_harm"],
                "PA":z["metrics"]["PA"],"MCC":z["metrics"]["MCC"],
                "falseS_rate":z["metrics"]["falseS_rate"],
                "S":z["metrics"]["S"],"NS":z["metrics"]["NS"],"NA":z["metrics"]["NA"],
            })
    csvwrite(OUT/"oracle_policy.csv",oracle_rows)

    rows=[]
    for source,target in (("052","053"),("053","052")):
        src=true_pools[source];tgt=true_pools[target];shapes=source_shapes(src)
        oname,safe,_=oracle_cache[(source,target)]
        rows.append(one_run(source,target,src,tgt,"zero_label",0,0,shapes,oname,safe))
        print("064",source,"->",target,"zero",oname,flush=True)
        for strategy in ("random_global","active_policy"):
            for budget in BUDGETS[1:]:
                for rep in range(REPS):
                    rows.append(one_run(source,target,src,tgt,strategy,budget,rep,
                                        shapes,oname,safe))
                print("064",source,"->",target,strategy,budget,flush=True)

    csvwrite(OUT/"replicate_results.csv",rows)
    summary=summarize(rows)
    for r in summary:
        r["direction_pass"]=direction_pass(r)
    csvwrite(OUT/"summary.csv",summary)

    min_budget=minimum_active_budget(summary)
    zero={f'{r["source"]}->{r["target"]}':r["selected_policy"]
          for r in rows if r["budget"]==0}
    oracle={f"{s}->{t}":oracle_cache[(s,t)][0]
            for s,t in (("052","053"),("053","052"))}
    run={
        "status":"PASS","git_head":fr["git_head"],
        "new_api_calls":0,"reserved_used":False,
        "actual_unlabeled_sha256_before_gt_evaluation":blind_sha,
        "pools":{k:len(v) for k,v in true_pools.items()},
        "oracle_policy":oracle,
        "zero_label_selected":zero,
        "minimum_active_budget":min_budget,
        "missing_link_closed":bool(min_budget is not None),
    }
    put(OUT/"run_summary.json",run)
    write_report(blind_rows,oracle_rows,summary,run)
    print("064 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(blind_rows,oracle_rows,summary,run):
    lines=[
        "# 064：Target-local Safe Policy Selection","",
        "## 核心变化","",
        "不再重建target分类器。只在Frozen PriorG附近认证局部Veto/Rescue policy；证据不足时回退BASE。source只提供每个policy-signature的弱先验（等效1个target label）。","",
        "## GT-blind结构","",
        "| direction | disagreement claims | zero-label selected | policy changes |",
        "|---|---:|---|---|",
    ]
    for r in blind_rows:
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["disagreement_n"]} | '
            f'{r["zero_label_selected"]} | {r["policy_changes"]} |')
    lines += [
        "",
        "## Oracle-safe policy（仅诊断）","",
        "| direction | oracle | safe nonBASE policies |",
        "|---|---|---|",
    ]

    for source,target in (("052","053"),("053","052")):
        rr=[r for r in oracle_rows if r["source"]==source and r["target"]==target]
        o=next(r["policy"] for r in rr if r["oracle_selected"])
        safe=[r["policy"] for r in rr if r["oracle_safe"] and r["policy"]!="BASE"]
        lines.append(f'| {source}→{target} | {o} | {", ".join(safe) if safe else "None"} |')

    lines += [
        "",
        "## Few-label结果","",
        "| direction | strategy | budget | oracle match | safe switch | unsafe switch | BASE fallback | ΔPA | ΔMCC | ΔNS | ΔNA | labels S/NS/NA | pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in summary:
        if r["budget"]==0:
            continue
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["strategy"]} | {r["budget"]} | '
            f'{r["oracle_match_rate"]:.1%} | {r["beneficial_nonbase_select_rate"]:.1%} | '
            f'{r["unsafe_switch_rate"]:.1%} | {r["base_fallback_rate"]:.1%} | '
            f'{r["mean_delta_PA"]:+.3f} | {r["mean_delta_MCC"]:+.3f} | '
            f'{r["mean_delta_NS"]:+.3f} | {r["mean_delta_NA"]:+.3f} | '
            f'{r["mean_labeled_S"]:.1f}/{r["mean_labeled_NS"]:.1f}/{r["mean_labeled_NA"]:.1f} | '
            f'{r["direction_pass"]} |')

    lines += ["","## 结论",""]
    if run["missing_link_closed"]:
        lines += [
            f'**active_policy在budget={run["minimum_active_budget"]}时，两方向同时满足预注册“该切换时切换、该回退时回退”标准。**',
            "",
            "在当前development setting下，少量target标签已经能够用于局部policy认证，而无需恢复完整Judge reliability或重建target分类器。",
        ]
    else:
        lines += [
            "**0/3/5/10/20个target标签下，active_policy仍未在两个方向同时闭合链路。**",
            "",
            "这说明即使把问题降成局部policy认证，当前policy库/认证规则仍不足；应结合oracle-safe结构判断是policy覆盖不足还是认证过于保守。",
        ]
    lines += [
        "",
        "## 边界","",
        "- policy library受既有development分析启发，真实052/053不是独立外部验证。",
        "- rescue允许posterior mean false-rescue rate最多25%，而不是要求global false-S绝对不增加。",
        "- oracle仅定义当前环境正确的切换/回退，不参与few-label选择。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv:
        self_test()
    else:
        main()
