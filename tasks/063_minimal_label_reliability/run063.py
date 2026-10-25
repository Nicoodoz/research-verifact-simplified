from pathlib import Path
import csv, hashlib, importlib.util, json, math, subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/063_minimal_label_reliability"
O055=ROOT/"outputs/055_zero_label_policy_adaptation"
P061=ROOT/"tasks/061_prior_anchored_drift/run061.py"

spec=importlib.util.spec_from_file_location("r061",P061)
r061=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r061)

LABS=("Supported","Not Supported","Not Addressed")
K=3
BUDGETS=(0,5,10,20,40)
REPS=50
SEED=20260922063
KAPPAS=(1.,3.,10.,30.,100.)
SOURCE_ALPHA=.5

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read_jsonl(p):
    with Path(p).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]
def put(p,obj):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def csvwrite(p,rows):
    rows=list(rows)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(p).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader(); w.writerows(rows)

def qwen_hard(scores):
    a=np.array([float(scores[k]) for k in LABS],float)
    return int(np.argmax(a))

def load_pool(tag,include_gt=True):
    raw=read_jsonl(O055/f"features_qwen_{tag}.jsonl")
    base=r061.load_pool(tag,include_gt=include_gt)
    out=[]
    for x,b in zip(raw,base):
        ds=int(r061.ds_hard(np.asarray([b["ds_rel"]]))[0])
        q=qwen_hard(x["qwen_scores"])
        row=dict(b)
        row["ds"]=ds; row["qwen"]=q; row["pattern"]=3*ds+q
        out.append(row)
    return out

def source_pattern_probs(rows):
    C=np.full((K,9),SOURCE_ALPHA,float)
    for r in rows:
        C[r["y"],r["pattern"]]+=1
    return C/C.sum(axis=1,keepdims=True)

def target_prior(source_rows,target_rows):
    rel=np.stack([r["ds_rel"] for r in target_rows])
    return r061.bbse_prior(source_rows,rel)

def reliability(Ps,labeled,kappa):
    C=np.asarray(Ps,float)*float(kappa)
    for r in labeled:
        C[r["y"],r["pattern"]]+=1
    return C/C.sum(axis=1,keepdims=True)

def predict_patterns(P,pi,rows):
    pat=np.array([r["pattern"] for r in rows],int)
    S=np.log(np.maximum(pi,1e-12))[None,:] + np.log(np.maximum(P[:,pat].T,1e-12))
    return np.argmax(S,axis=1)

def posterior_pattern(Ps,pi,p):
    x=np.asarray(pi)*Ps[:,int(p)]
    x=np.maximum(x,1e-15); x/=x.sum()
    return x

def choose_kappa(Ps,pi,labeled):
    if len(labeled)<=1:
        return max(KAPPAS)
    best=None
    for kappa in KAPPAS:
        nll=[]
        for i,r in enumerate(labeled):
            tr=labeled[:i]+labeled[i+1:]
            P=reliability(Ps,tr,kappa)
            post=posterior_pattern(P,pi,r["pattern"])
            nll.append(-math.log(max(post[r["y"]],1e-12)))
        key=(float(np.mean(nll)),-float(kappa))
        if best is None or key<best[0]:
            best=(key,float(kappa))
    return best[1]

def mcc(y,p):
    M=np.zeros((K,K),float)
    np.add.at(M,(y,p),1)
    s=M.sum(); c=np.trace(M); a=M.sum(1); b=M.sum(0)
    den=((s*s-a@a)*(s*s-b@b))**.5
    return float((c*s-a@b)/den) if den else 0.0

def metrics(rows,pred):
    y=np.array([r["y"] for r in rows],int)
    pred=np.asarray(pred,int)
    M=np.zeros((K,K),int); np.add.at(M,(y,pred),1)
    rec=np.array([M[k,k]/M[k].sum() if M[k].sum() else np.nan for k in range(K)])

    nonS=max(int(np.sum(y!=0)),1)
    falseS=int(np.sum((y!=0)&(pred==0)))
    return {
        "PA":float(np.mean(y==pred)),
        "MCC":mcc(y,pred),
        "falseS":falseS,
        "falseS_rate":falseS/nonS,
        "S":float(rec[0]),"NS":float(rec[1]),"NA":float(rec[2]),
        "correct":int(np.sum(y==pred)),
        "n":len(y),
    }

def frozen_pred(rows):
    return np.array([r["ds"] for r in rows],int)

def seeded_rng(source,target,strategy,rep):
    s=f"{SEED}:{source}:{target}:{strategy}:{rep}"
    h=hashlib.sha256(s.encode()).hexdigest()
    return np.random.default_rng(int(h[:16],16))

def diverse_order(rows,rng):
    by={}
    for i,r in enumerate(rows): by.setdefault(r["sid"],[]).append(i)
    sids=list(by); rng.shuffle(sids)
    for sid in sids: rng.shuffle(by[sid])
    out=[]; depth=0
    while True:
        added=False
        order=sids.copy(); rng.shuffle(order)

        for sid in order:
            if depth<len(by[sid]):
                out.append(by[sid][depth]); added=True
        if not added: break
        depth+=1
    return out

def select_random(rows,budget,rng):
    return diverse_order(rows,rng)[:budget]

def pattern_entropy(Ps,pi):
    H=np.zeros(9,float)
    for p in range(9):
        q=posterior_pattern(Ps,pi,p)
        H[p]=-float(np.sum(q*np.log(np.maximum(q,1e-12))))
    return H

def select_active(rows,budget,Ps,pi,rng):
    H=pattern_entropy(Ps,pi)
    selected=[]; used=set(); pc=np.zeros(9,int)
    tie=rng.random(len(rows))
    remain=set(range(len(rows)))
    for _ in range(min(budget,len(rows))):
        unseen=[i for i in remain if rows[i]["sid"] not in used]
        cand=unseen if unseen else list(remain)
        i=max(cand,key=lambda j:(H[rows[j]["pattern"]]/(1+pc[rows[j]["pattern"]]),tie[j]))
        selected.append(i); remain.remove(i); used.add(rows[i]["sid"]); pc[rows[i]["pattern"]]+=1
    return selected

def select_oracle_balanced(rows,budget,rng):
    by_class={k:[] for k in range(K)}
    for i,r in enumerate(rows): by_class[r["y"]].append(i)
    for k in range(K): rng.shuffle(by_class[k])
    selected=[]; used=set(); counts=np.zeros(K,int)
    remain={k:set(v) for k,v in by_class.items()}
    for _ in range(min(budget,len(rows))):
        avail=[k for k in range(K) if remain[k]]
        if not avail: break
        k=min(avail,key=lambda z:(counts[z],z))
        unseen=[i for i in remain[k] if rows[i]["sid"] not in used]
        cand=unseen if unseen else list(remain[k])
        i=cand[int(rng.integers(len(cand)))]
        selected.append(i); remain[k].remove(i)
        used.add(rows[i]["sid"]); counts[k]+=1
    return selected

def select_indices(strategy,rows,budget,Ps,pi,rng):
    if budget==0: return []
    if strategy=="random": return select_random(rows,budget,rng)
    if strategy=="active": return select_active(rows,budget,Ps,pi,rng)
    if strategy=="oracle_balanced": return select_oracle_balanced(rows,budget,rng)
    raise ValueError(strategy)

def safe_win(adapt,base):
    return bool(
        adapt["PA"]>=base["PA"]-1e-12 and
        adapt["MCC"]>=base["MCC"]-1e-12 and
        adapt["falseS_rate"]<=base["falseS_rate"]+1e-12 and
        adapt["NS"]>=base["NS"]-1e-12 and
        adapt["NA"]>=base["NA"]-.02-1e-12 and
        (adapt["PA"]>base["PA"]+1e-12 or adapt["MCC"]>base["MCC"]+1e-12)
    )

def one_run(source,target,source_rows,target_rows,strategy,budget,rep,Ps,pi):
    rng=seeded_rng(source,target,strategy,rep)
    idx=select_indices(strategy,target_rows,budget,Ps,pi,rng)
    sel=set(idx)
    labeled=[target_rows[i] for i in idx]
    hold=[r for i,r in enumerate(target_rows) if i not in sel]
    kappa=choose_kappa(Ps,pi,labeled) if budget else 100.0
    P=reliability(Ps,labeled,kappa)
    adapt_pred=predict_patterns(P,pi,hold)
    base_pred=frozen_pred(hold)
    am=metrics(hold,adapt_pred); bm=metrics(hold,base_pred)

    all_pred=predict_patterns(P,pi,target_rows)
    if idx:
        for i in idx: all_pred[i]=target_rows[i]["y"]
    op=metrics(target_rows,all_pred)
    lc=np.bincount([r["y"] for r in labeled],minlength=K) if labeled else np.zeros(K,int)

    row={
        "source":source,"target":target,"strategy":strategy,
        "budget":budget,"rep":rep,"kappa":kappa,
        "labeled_S":int(lc[0]),"labeled_NS":int(lc[1]),"labeled_NA":int(lc[2]),
        "holdout_n":am["n"],"safe_win":safe_win(am,bm),
    }
    for pref,m in (("adapt",am),("base",bm),("operation",op)):
        for k,v in m.items(): row[f"{pref}_{k}"]=v
    for k in ("PA","MCC","falseS_rate","S","NS","NA"):
        row[f"delta_{k}"]=am[k]-bm[k]
    return row

def mean_or_nan(vals):
    a=np.asarray(vals,float)
    a=a[np.isfinite(a)]
    return float(a.mean()) if len(a) else float("nan")

def summarize(rows):
    out=[]
    keys=sorted(set((r["source"],r["target"],r["strategy"],r["budget"]) for r in rows))
    for source,target,strategy,budget in keys:
        x=[r for r in rows if (r["source"],r["target"],r["strategy"],r["budget"])==(source,target,strategy,budget)]
        z={"source":source,"target":target,"strategy":strategy,"budget":budget,"reps":len(x)}
        for k in ("delta_PA","delta_MCC","delta_falseS_rate","delta_S","delta_NS","delta_NA"):
            z[f"mean_{k}"]=mean_or_nan([r[k] for r in x])
        z["safe_win_rate"]=float(np.mean([r["safe_win"] for r in x]))

        for k in ("labeled_S","labeled_NS","labeled_NA","kappa"):
            z[f"mean_{k}"]=mean_or_nan([r[k] for r in x])
        for k in ("adapt_PA","adapt_MCC","adapt_falseS_rate","adapt_NS","adapt_NA",
                  "base_PA","base_MCC","base_falseS_rate","base_NS","base_NA",
                  "operation_PA","operation_MCC","operation_falseS_rate"):
            z[f"mean_{k}"]=mean_or_nan([r[k] for r in x])
        z["deployment_pass"]=bool(
            z["mean_delta_PA"]>=0 and
            z["mean_delta_MCC"]>=.02 and
            z["mean_delta_falseS_rate"]<=0 and
            z["mean_delta_NS"]>=0 and
            z["mean_delta_NA"]>=-.02 and
            z["safe_win_rate"]>=.70
        )
        out.append(z)
    return out

def conditional_diagnostics(rows):
    out=[]
    for source,target,strategy,budget in sorted(set(
        (r["source"],r["target"],r["strategy"],r["budget"]) for r in rows if r["budget"]>0)):
        x=[r for r in rows if (r["source"],r["target"],r["strategy"],r["budget"])==(source,target,strategy,budget)]
        for name,fn in (
            ("has_NS1",lambda r:r["labeled_NS"]>=1),
            ("has_NS2",lambda r:r["labeled_NS"]>=2),
            ("has_NA1",lambda r:r["labeled_NA"]>=1),
        ):
            y=[r for r in x if fn(r)]
            if not y: continue
            out.append({
                "source":source,"target":target,"strategy":strategy,"budget":budget,
                "condition":name,"n_reps":len(y),
                "mean_delta_MCC":mean_or_nan([r["delta_MCC"] for r in y]),
                "mean_delta_NS":mean_or_nan([r["delta_NS"] for r in y]),
                "mean_delta_NA":mean_or_nan([r["delta_NA"] for r in y]),
                "mean_delta_falseS_rate":mean_or_nan([r["delta_falseS_rate"] for r in y]),
                "safe_win_rate":float(np.mean([r["safe_win"] for r in y])),
            })
    return out

def freeze():
    inputs={
        "features_qwen_052":O055/"features_qwen_052.jsonl",
        "features_qwen_053":O055/"features_qwen_053.jsonl",
        "run061":P061,
        "protocol":ROOT/"tasks/063_minimal_label_reliability/protocol.md",
    }
    obj={
        "git_head":subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"budgets":list(BUDGETS),"reps":REPS,
        "kappas":list(KAPPAS),"source_alpha":SOURCE_ALPHA,
        "code_sha256":sha(Path(__file__)),
        "inputs":{k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)}
                  for k,v in inputs.items()},
    }
    put(OUT/"freeze.json",obj)
    return obj

def self_test():
    pools={k:load_pool(k,True) for k in ("052","053")}
    assert len(pools["052"])==236 and len(pools["053"])==237
    p1=target_prior(pools["052"],pools["053"])
    p2=target_prior(pools["053"],pools["052"])
    e1=np.array([.8164057926659678,.06417253409756984,.11942167323646236])
    e2=np.array([.7847781047562029,.06826853183129573,.14695336341250134])
    assert np.max(np.abs(p1-e1))<1e-6 and np.max(np.abs(p2-e2))<1e-6
    Ps=source_pattern_probs(pools["052"]); assert np.allclose(Ps.sum(1),1)

    blind=load_pool("053",False)
    rng=seeded_rng("052","053","active",0)
    ia=select_active(pools["053"],10,Ps,p1,rng)
    rng=seeded_rng("052","053","active",0)
    ib=select_active(blind,10,Ps,p1,rng)
    assert ia==ib
    z=one_run("052","053",pools["052"],pools["053"],
              "active",10,0,Ps,p1)
    assert z["holdout_n"]==227
    print("063 SELF-TEST PASS",{
        "bbse_052_053":p1.tolist(),
        "bbse_053_052":p2.tolist(),
        "active10_labels":[z["labeled_S"],z["labeled_NS"],z["labeled_NA"]],
        "delta_mcc":z["delta_MCC"],"safe_win":z["safe_win"],
    })

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("freeze.json","replicate_results.csv","summary.csv"):
        if (OUT/name).exists():
            raise RuntimeError("formal output exists: "+name)
    fr=freeze()
    pools={k:load_pool(k,True) for k in ("052","053")}
    rows=[]

    for source,target in (("052","053"),("053","052")):
        src=pools[source]; tgt=pools[target]
        Ps=source_pattern_probs(src)
        pi=target_prior(src,tgt)
        rows.append(one_run(source,target,src,tgt,"zero",0,0,Ps,pi))
        print("063",source,"->",target,"budget 0",flush=True)
        for strategy in ("random","active","oracle_balanced"):
            for budget in BUDGETS[1:]:
                for rep in range(REPS):
                    rows.append(one_run(
                        source,target,src,tgt,strategy,budget,rep,Ps,pi))
                print("063",source,"->",target,strategy,budget,flush=True)

    csvwrite(OUT/"replicate_results.csv",rows)
    summary=summarize(rows)
    csvwrite(OUT/"summary.csv",summary)
    cond=conditional_diagnostics(rows)
    csvwrite(OUT/"conditional_diagnostics.csv",cond)

    def minimum_passing(strategy):
        vals=[]
        for b in BUDGETS[1:]:
            rr=[r for r in summary if r["strategy"]==strategy and r["budget"]==b]
            if len(rr)==2 and all(r["deployment_pass"] for r in rr):
                vals.append(b)
        return min(vals) if vals else None

    mins={s:minimum_passing(s) for s in ("random","active","oracle_balanced")}
    active_min=mins["active"]
    if active_min is not None:
        diagnosis="active_few_label_link_closed"
    elif mins["oracle_balanced"] is not None:
        diagnosis="labels_sufficient_but_acquisition_is_bottleneck"
    else:
        diagnosis="joint_pattern_reliability_calibrator_insufficient_by_40_labels"

    run={
        "status":"PASS","git_head":fr["git_head"],
        "new_api_calls":0,"reserved_used":False,
        "pools":{k:len(v) for k,v in pools.items()},
        "minimum_passing_budget":mins,
        "diagnosis":diagnosis,
        "missing_link_closed":bool(active_min is not None),
    }
    put(OUT/"run_summary.json",run)
    write_report(summary,cond,run)
    print("063 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(summary,cond,run):
    lines=[
        "# 063：Minimal-label Target Reliability Calibration","",
        "## 方法","",
        "固定BBSE target prior；只用Frozen PriorG与Qwen U0两个Judge的9种joint pattern。source给出P(pattern|Y)作为Dirichlet prior，few target labels更新target reliability；kappa仅在few-label subset内部LOO选择。","",
        "主评估在未标注holdout claims上，与同一holdout的Frozen PriorG比较。","",
        "## 预算结果","",
        "| direction | strategy | budget | ΔPA | ΔMCC | Δfalse-S rate | ΔNS | ΔNA | safe-win | labels S/NS/NA | pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for r in summary:
        if r["budget"]==0: continue
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["strategy"]} | {r["budget"]} | '
            f'{r["mean_delta_PA"]:+.3f} | {r["mean_delta_MCC"]:+.3f} | '
            f'{r["mean_delta_falseS_rate"]:+.3f} | {r["mean_delta_NS"]:+.3f} | '
            f'{r["mean_delta_NA"]:+.3f} | {r["safe_win_rate"]:.1%} | '
            f'{r["mean_labeled_S"]:.1f}/{r["mean_labeled_NS"]:.1f}/{r["mean_labeled_NA"]:.1f} | '
            f'{r["deployment_pass"]} |')

    lines += [
        "",
        "## 最小通过budget","",
        f'- random: **{run["minimum_passing_budget"]["random"]}**',
        f'- active: **{run["minimum_passing_budget"]["active"]}**',
        f'- oracle-balanced（诊断）: **{run["minimum_passing_budget"]["oracle_balanced"]}**',
        "",
        "## 结论","",
    ]
    if run["diagnosis"]=="active_few_label_link_closed":
        lines += [
            f'**active few-label在budget={run["minimum_passing_budget"]["active"]}时，两方向同时达到事前安全改善标准。**',
            "",
            "这意味着BBSE prevalence + 少量target reliability labels已经能够补上zero-label缺失链路；下一步可以把该calibrator接入safe dynamic decision并做更独立验证。",
        ]
    elif run["diagnosis"]=="labels_sufficient_but_acquisition_is_bottleneck":
        lines += [
            "**oracle-balanced能通过，但可部署active未通过。**",
            "",
            "标签数量本身已经足够；主要问题变成如何稳定获得NS/NA信息，而不是calibration模型本身。",
        ]
    else:
        lines += [
            "**到40个target labels，oracle-balanced也没有让当前joint-pattern reliability calibrator两方向同时通过。**",
            "",
            "因此不能说missing link已补齐；需要比9-pattern reliability table更有表达力的few-label calibrator。",
        ]
    lines += [
        "",
        "## 边界","",
        "- oracle-balanced知道target GT，仅作信息上限。",
        "- 052/053仍是development内部池。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv: self_test()
    else: main()
