from pathlib import Path
import hashlib, importlib.util, json, math, subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/063_minimal_label_reliability"
P063=ROOT/"tasks/063_minimal_label_reliability/run063.py"

spec=importlib.util.spec_from_file_location("r063",P063)
r063=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r063)

K=3
BUDGETS=r063.BUDGETS
REPS=r063.REPS
KAPPAS=r063.KAPPAS
SEED=202609220631
RIDGE=.1

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,obj):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

class SoftLDA:
    def __init__(self,rows):
        self.U=np.stack([r["u"] for r in rows])
        self.y=np.array([r["y"] for r in rows],int)
        self.mean=self.U.mean(0); self.std=self.U.std(0)
        self.std[self.std<1e-8]=1.0

        self.Z=(self.U-self.mean)/self.std
        self.mu=np.stack([self.Z[self.y==k].mean(0) for k in range(K)])
        R=np.vstack([self.Z[self.y==k]-self.mu[k] for k in range(K)])
        self.cov=np.cov(R,rowvar=False,bias=True)+RIDGE*np.eye(4)
        self.inv=np.linalg.inv(self.cov)

    def transform_rows(self,rows):
        U=np.stack([r["u"] for r in rows])
        return (U-self.mean)/self.std

    def adapted_means(self,labeled,kappa):
        mu=self.mu.copy()
        if not labeled: return mu
        Z=self.transform_rows(labeled)
        y=np.array([r["y"] for r in labeled],int)
        for k in range(K):
            zk=Z[y==k]
            if len(zk):
                mu[k]=(kappa*self.mu[k]+zk.sum(0))/(kappa+len(zk))
        return mu

    def posterior_Z(self,Z,pi,mu):
        Z=np.asarray(Z,float)
        L=np.empty((len(Z),K),float)
        for k in range(K):
            d=Z-mu[k]
            L[:,k]=math.log(max(float(pi[k]),1e-12))-.5*np.einsum("ni,ij,nj->n",d,self.inv,d)
        L-=L.max(1,keepdims=True)
        P=np.exp(L); P/=P.sum(1,keepdims=True)
        return P

    def predict(self,rows,pi,mu):
        if not rows: return np.array([],int)
        P=self.posterior_Z(self.transform_rows(rows),pi,mu)
        return np.argmax(P,axis=1)

    def choose_kappa(self,labeled,pi):
        if len(labeled)<=1: return max(KAPPAS)
        best=None
        for kappa in KAPPAS:
            nll=[]
            for i,r in enumerate(labeled):
                tr=labeled[:i]+labeled[i+1:]
                mu=self.adapted_means(tr,kappa)
                z=self.transform_rows([r])
                post=self.posterior_Z(z,pi,mu)[0]
                nll.append(-math.log(max(float(post[r["y"]]),1e-12)))
            key=(float(np.mean(nll)),-float(kappa))
            if best is None or key<best[0]: best=(key,float(kappa))
        return best[1]

def seeded_rng(source,target,strategy,rep):
    h=hashlib.sha256(f"{SEED}:{source}:{target}:{strategy}:{rep}".encode()).hexdigest()
    return np.random.default_rng(int(h[:16],16))

def select_active_soft(rows,budget,model,pi,rng):
    Z=model.transform_rows(rows)
    P=model.posterior_Z(Z,pi,model.mu)
    H=-np.sum(P*np.log(np.maximum(P,1e-12)),axis=1)
    pred=np.argmax(P,axis=1)
    tie=rng.random(len(rows))

    selected=[]; used=set(); cc=np.zeros(K,int)
    remain=set(range(len(rows)))
    for _ in range(min(budget,len(rows))):
        unseen=[i for i in remain if rows[i]["sid"] not in used]
        cand=unseen if unseen else list(remain)
        i=max(cand,key=lambda j:(H[j]/(1+cc[pred[j]]),tie[j]))
        selected.append(i); remain.remove(i)
        used.add(rows[i]["sid"]); cc[pred[i]]+=1
    return selected

def select_indices(strategy,rows,budget,model,pi,rng):
    if budget==0: return []
    if strategy=="random":
        return r063.select_random(rows,budget,rng)
    if strategy=="active_soft":
        return select_active_soft(rows,budget,model,pi,rng)
    if strategy=="oracle_balanced":
        return r063.select_oracle_balanced(rows,budget,rng)
    raise ValueError(strategy)

def one_run(source,target,src,tgt,strategy,budget,rep,model,pi):
    rng=seeded_rng(source,target,strategy,rep)
    idx=select_indices(strategy,tgt,budget,model,pi,rng)
    sel=set(idx)
    labeled=[tgt[i] for i in idx]
    hold=[r for i,r in enumerate(tgt) if i not in sel]

    kappa=model.choose_kappa(labeled,pi) if budget else 100.0
    mu=model.adapted_means(labeled,kappa)
    ap=model.predict(hold,pi,mu)
    bp=r063.frozen_pred(hold)
    am=r063.metrics(hold,ap); bm=r063.metrics(hold,bp)

    allp=model.predict(tgt,pi,mu)
    for i in idx: allp[i]=tgt[i]["y"]
    op=r063.metrics(tgt,allp)
    lc=np.bincount([r["y"] for r in labeled],minlength=K) if labeled else np.zeros(K,int)
    row={
        "source":source,"target":target,"strategy":strategy,
        "budget":budget,"rep":rep,"kappa":kappa,
        "labeled_S":int(lc[0]),"labeled_NS":int(lc[1]),"labeled_NA":int(lc[2]),
        "holdout_n":am["n"],"safe_win":r063.safe_win(am,bm),
    }
    for pref,m in (("adapt",am),("base",bm),("operation",op)):
        for k,v in m.items(): row[f"{pref}_{k}"]=v
    for k in ("PA","MCC","falseS_rate","S","NS","NA"):
        row[f"delta_{k}"]=am[k]-bm[k]
    return row

def freeze():
    inputs={
        "features_qwen_052":r063.O055/"features_qwen_052.jsonl",
        "features_qwen_053":r063.O055/"features_qwen_053.jsonl",
        "run063":P063,
        "amendment":ROOT/"tasks/063_minimal_label_reliability/protocol_amendment_001.md",
    }
    obj={
        "git_head":subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"budgets":list(BUDGETS),"reps":REPS,
        "kappas":list(KAPPAS),"ridge":RIDGE,
        "code_sha256":sha(Path(__file__)),
        "inputs":{k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)}
                  for k,v in inputs.items()},
    }
    put(OUT/"soft_freeze.json",obj)
    return obj

def self_test():
    pools={k:r063.load_pool(k,True) for k in ("052","053")}
    model=SoftLDA(pools["052"])
    pi=r063.target_prior(pools["052"],pools["053"])
    blind=r063.load_pool("053",False)
    rng=seeded_rng("052","053","active_soft",0)
    a=select_active_soft(pools["053"],10,model,pi,rng)
    rng=seeded_rng("052","053","active_soft",0)
    b=select_active_soft(blind,10,model,pi,rng)
    assert a==b

    z=one_run("052","053",pools["052"],pools["053"],
              "active_soft",10,0,model,pi)
    assert z["holdout_n"]==227
    print("063 SOFT SELF-TEST PASS",{
        "labels":[z["labeled_S"],z["labeled_NS"],z["labeled_NA"]],
        "kappa":z["kappa"],"delta_mcc":z["delta_MCC"],
        "delta_ns":z["delta_NS"],"safe_win":z["safe_win"],
    })

def main():
    for name in ("soft_freeze.json","soft_replicate_results.csv","soft_summary.csv"):
        if (OUT/name).exists(): raise RuntimeError("formal output exists: "+name)
    fr=freeze()
    pools={k:r063.load_pool(k,True) for k in ("052","053")}
    rows=[]
    for source,target in (("052","053"),("053","052")):
        src=pools[source]; tgt=pools[target]
        model=SoftLDA(src)
        pi=r063.target_prior(src,tgt)
        rows.append(one_run(source,target,src,tgt,"zero",0,0,model,pi))
        print("063 soft",source,"->",target,"budget 0",flush=True)
        for strategy in ("random","active_soft","oracle_balanced"):
            for budget in BUDGETS[1:]:
                for rep in range(REPS):
                    rows.append(one_run(
                        source,target,src,tgt,strategy,budget,rep,model,pi))
                print("063 soft",source,"->",target,strategy,budget,flush=True)

    r063.csvwrite(OUT/"soft_replicate_results.csv",rows)
    summary=r063.summarize(rows)
    r063.csvwrite(OUT/"soft_summary.csv",summary)
    cond=r063.conditional_diagnostics(rows)
    r063.csvwrite(OUT/"soft_conditional_diagnostics.csv",cond)

    def minimum_passing(strategy):
        vals=[]
        for b in BUDGETS[1:]:
            rr=[r for r in summary if r["strategy"]==strategy and r["budget"]==b]
            if len(rr)==2 and all(r["deployment_pass"] for r in rr):
                vals.append(b)
        return min(vals) if vals else None

    mins={s:minimum_passing(s) for s in ("random","active_soft","oracle_balanced")}
    if mins["active_soft"] is not None:
        diagnosis="soft_active_link_closed"
    elif mins["oracle_balanced"] is not None:
        diagnosis="soft_labels_sufficient_acquisition_bottleneck"
    else:
        diagnosis="soft_mean_calibrator_insufficient_by_40"
    run={
        "status":"PASS","git_head":fr["git_head"],
        "new_api_calls":0,"reserved_used":False,
        "pools":{k:len(v) for k,v in pools.items()},
        "minimum_passing_budget":mins,
        "diagnosis":diagnosis,
        "missing_link_closed":bool(mins["active_soft"] is not None),
    }
    put(OUT/"soft_run_summary.json",run)
    write_report(summary,run)
    print("063 SOFT COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(summary,run):
    lines=[
        "# 063 Amendment 001：Soft-score Few-label Calibration","",
        "## 方法","",
        "保留4维DeepSeek/Qwen log-odds。source提供class means与pooled covariance；few target labels用shrinkage直接更新S/NS/NA各自target mean；target prior固定BBSE。","",
        "## 预算结果","",
        "| direction | strategy | budget | ΔPA | ΔMCC | Δfalse-S | ΔNS | ΔNA | safe-win | labels S/NS/NA | pass |",
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
        f'- active_soft: **{run["minimum_passing_budget"]["active_soft"]}**',
        f'- oracle-balanced: **{run["minimum_passing_budget"]["oracle_balanced"]}**',
        "",
        "## 结论","",
    ]
    if run["diagnosis"]=="soft_active_link_closed":
        lines += [
            f'**active_soft在budget={run["minimum_passing_budget"]["active_soft"]}时两方向同时通过。**',
            "",
            "在当前development setting下，BBSE + minimal target labels已经补齐conditional reliability缺口。",
        ]
    elif run["diagnosis"]=="soft_labels_sufficient_acquisition_bottleneck":
        lines += [
            "**oracle-balanced通过，但active_soft未通过。**",
            "",
            "few-label信息量已经足够，下一瓶颈是如何稳定获取少数类信息。",
        ]
    else:
        lines += [
            "**到40 labels，oracle-balanced仍未让soft mean calibrator两方向同时通过。**",
            "",
            "few-label方向仍有信息，但当前均值校准还不足以声称链路闭合。",
        ]
    lines += [
        "",
        "## 边界","",
        "- 本结果是主063失败后的独立amendment。",
        "- oracle-balanced不是部署策略。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"soft_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv: self_test()
    else: main()
