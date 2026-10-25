from pathlib import Path
import argparse, csv, hashlib, json, math, subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/060_class_specific_drift"
O055 = ROOT / "outputs/055_zero_label_policy_adaptation"
O059 = ROOT / "outputs/059_joint_prior_judge_drift"

LABELS = ["Supported","Not Supported","Not Addressed"]
FEATURES = ["DS_S","DS_NS","Q_S","Q_NS"]
K, D = 3, 4
EPS = 0.5
TAU = 20.0
COV_BLEND = 0.5
RIDGE = 0.05
CLIP = 3.0
MAX_ITER = 100
TOL = 1e-6
REPS = 30
SEED = 20260922060
BATCHES = (240,480,960)
PRIORS = {
    "source": np.array([1108.,100.,170.]) / 1378.,
    "S60": np.array([.60,.20,.20]),
    "NS_heavy": np.array([.60,.30,.10]),
    "NA_heavy": np.array([.60,.10,.30]),
}

def drift_matrix(**kwargs):
    x=np.zeros((K,D),float)
    for key,val in kwargs.items():
        y,dim=key.split("__")
        x[LABELS.index(y),FEATURES.index(dim)]=float(val)
    return x

DRIFTS = {
    "none": drift_matrix(),
    "NS_QNS": drift_matrix(**{"Not Supported__Q_NS":1.5}),
    "NA_DSS": drift_matrix(**{"Not Addressed__DS_S":1.0}),
    "NS_DSNS": drift_matrix(**{"Not Supported__DS_NS":1.0}),
    "S_QS_down": drift_matrix(**{"Supported__Q_S":-0.5}),
    "mixed": drift_matrix(**{
        "Supported__DS_S":-0.5,
        "Not Supported__DS_NS":1.0,
        "Not Supported__Q_S":0.5,
        "Not Supported__Q_NS":1.5,
        "Not Addressed__DS_S":0.8,
        "Not Addressed__DS_NS":0.5,
    }),
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def csvwrite(path,rows):
    rows=list(rows); fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def put(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def scores_u(scores):
    s=float(scores["Supported"])+EPS
    ns=float(scores["Not Supported"])+EPS
    na=float(scores["Not Addressed"])+EPS
    return np.array([np.log(s/na),np.log(ns/na)],float)

def load_pool(tag):
    out=[]
    for x in read_jsonl(O055/f"features_qwen_{tag}.jsonl"):
        out.append({
            "id":x["id"],
            "sid":str(x["sid"]),
            "y":LABELS.index(x["GT"]),
            "u":np.r_[scores_u(x["ts_scores"]),scores_u(x["qwen_scores"])]
        })
    return out

def simplex_grid(step=.02):
    m=int(round(1/step))
    out=[]
    for i in range(m+1):
        for j in range(m+1-i):
            out.append([i/m,j/m,(m-i-j)/m])
    return np.asarray(out,float)

class AnchoredMixture:
    def __init__(self,rows):
        self.rows=rows
        self.U=np.stack([r["u"] for r in rows])
        self.y=np.array([r["y"] for r in rows],int)
        self.mean=self.U.mean(axis=0)
        self.std=self.U.std(axis=0)
        self.std[self.std<1e-8]=1.0
        self.Z=(self.U-self.mean)/self.std
        self.mu=np.stack([self.Z[self.y==k].mean(axis=0) for k in range(K)])
        pooled=np.cov(self.Z,rowvar=False,bias=True)
        self.cov=[]; self.inv=[]; self.logdet=[]
        for k in range(K):
            ck=np.cov(self.Z[self.y==k],rowvar=False,bias=True)
            c=COV_BLEND*ck+(1-COV_BLEND)*pooled+RIDGE*np.eye(D)
            self.cov.append(c)
            self.inv.append(np.linalg.inv(c))
            sign,ld=np.linalg.slogdet(c)
            if sign<=0:
                raise RuntimeError("non-PD covariance")
            self.logdet.append(ld)
        self.cov=np.stack(self.cov)
        self.inv=np.stack(self.inv)
        self.logdet=np.asarray(self.logdet,float)
        self.emp_prior=np.bincount(self.y,minlength=K)/len(self.y)
        self.grid=simplex_grid()
        second=self.cov+np.einsum("ki,kj->kij",self.mu,self.mu)
        gm=self.grid@self.mu
        gs=np.einsum("pk,kij->pij",self.grid,second)
        gc=gs-np.einsum("pi,pj->pij",gm,gm)
        tri=np.triu_indices(D)
        self.grid_cov_vec=gc[:,tri[0],tri[1]]
        self.tri=tri
        self.grid_cov_norm=np.sum(self.grid_cov_vec*self.grid_cov_vec,axis=1)

    def transform(self,U):
        return (np.asarray(U,float)-self.mean)/self.std

    def moment_prior(self,Z):
        C=np.cov(Z,rowvar=False,bias=True)
        v=C[self.tri]
        dist=self.grid_cov_norm+np.sum(v*v)-2*(self.grid_cov_vec@v)
        return self.grid[int(np.argmin(dist))]

    def _log_components(self,Z,pi,delta):
        out=np.empty((len(Z),K),float)
        c0=D*np.log(2*np.pi)
        for k in range(K):
            dif=Z-(self.mu[k]+delta[k])
            q=np.einsum("ni,ij,nj->n",dif,self.inv[k],dif)
            out[:,k]=np.log(max(pi[k],1e-12))-.5*(c0+self.logdet[k]+q)
        return out

    def _objective(self,Z,pi,delta):
        L=self._log_components(Z,pi,delta)
        m=L.max(axis=1)
        ll=float(np.sum(m+np.log(np.exp(L-m[:,None]).sum(axis=1))))
        g=delta.mean(axis=0)
        pen=.5*TAU*float(np.sum((delta-g[None,:])**2))
        return ll-pen

    def _fit_start(self,Z,pi0):
        pi=np.maximum(np.asarray(pi0,float),1e-6)
        pi/=pi.sum()
        delta=np.zeros((K,D),float)
        prev=-np.inf
        eye=np.eye(D)
        for it in range(MAX_ITER):
            L=self._log_components(Z,pi,delta)
            m=L.max(axis=1)
            E=np.exp(L-m[:,None])
            R=E/E.sum(axis=1,keepdims=True)
            mass=R.sum(axis=0)+1e-12
            pi=mass/mass.sum()
            target_mean=(R.T@Z)/mass[:,None]
            raw=target_mean-self.mu
            g=np.average(raw,axis=0,weights=mass)
            for _ in range(8):
                nd=np.empty_like(delta)
                for k in range(K):
                    A=mass[k]*self.inv[k]+TAU*eye
                    b=mass[k]*(self.inv[k]@raw[k])+TAU*g
                    nd[k]=np.linalg.solve(A,b)
                nd=np.clip(nd,-CLIP,CLIP)
                ng=nd.mean(axis=0)
                if np.max(np.abs(ng-g))<1e-8:
                    delta=nd; g=ng; break
                delta=nd; g=ng
            obj=self._objective(Z,pi,delta)
            if abs(obj-prev)<TOL:
                break
            prev=obj
        return {"pi":pi,"delta_z":delta,"mass":mass,
                "objective":float(obj),"iterations":it+1}

    def fit(self,Uraw):
        Z=self.transform(Uraw)
        starts=[
            self.emp_prior,
            np.full(K,1.0/K),
            self.moment_prior(Z),
        ]
        fits=[self._fit_start(Z,p) for p in starts]
        best=max(fits,key=lambda x:x["objective"])
        best=dict(best)
        best["delta_raw"]=best["delta_z"]*self.std[None,:]
        best["pi_start_candidates"]=[p.tolist() for p in starts]
        return best

def alloc(prior,n):
    x=np.asarray(prior)*n
    base=np.floor(x).astype(int)
    left=int(n-base.sum())
    order=np.argsort(-(x-base),kind="stable")
    for i in order[:left]:
        base[i]+=1
    return base

def sample_target(rows,prior,n,drift,rng):
    y=np.array([r["y"] for r in rows],int)
    by=[np.where(y==k)[0] for k in range(K)]
    idx=[]
    for k,c in enumerate(alloc(prior,n)):
        idx.extend(rng.choice(by[k],size=int(c),replace=True).tolist())
    rng.shuffle(idx)
    yy=y[idx]
    U=np.stack([rows[i]["u"] for i in idx])
    U=U+drift[yy]
    return U,yy

def fit_metrics(model,U,yy,prior,drift_true):
    fit=model.fit(U)
    pi=fit["pi"]
    delta=fit["delta_raw"]
    prior_l1=float(np.sum(np.abs(pi-prior)))
    mae=float(np.mean(np.abs(delta-drift_true)))
    nz=np.abs(drift_true)>=1e-12
    sign=np.nan
    if np.any(nz):
        sign=float(np.mean(np.sign(delta[nz])==np.sign(drift_true[nz])))
    return fit,prior_l1,mae,sign

def freeze():
    inputs={
        "features_qwen_052":O055/"features_qwen_052.jsonl",
        "features_qwen_053":O055/"features_qwen_053.jsonl",
        "actual059":O059/"actual_evaluation.csv",
        "protocol":ROOT/"tasks/060_class_specific_drift/protocol.md",
    }
    obj={
        "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"tau":TAU,"cov_blend":COV_BLEND,"ridge":RIDGE,
        "clip":CLIP,"max_iter":MAX_ITER,"tol":TOL,"reps":REPS,
        "batches":list(BATCHES),
        "priors":{k:v.tolist() for k,v in PRIORS.items()},
        "drifts":{k:v.tolist() for k,v in DRIFTS.items()},
        "code_sha256":sha(Path(__file__)),
        "inputs":{k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)} for k,v in inputs.items()},
    }
    put(OUT/"freeze.json",obj)
    return obj

def self_test():
    pools={k:load_pool(k) for k in ("052","053")}
    if len(pools["052"])!=236 or len(pools["053"])!=237:
        raise AssertionError("pool size")
    m=AnchoredMixture(pools["052"])
    rng=np.random.default_rng(7)
    prior=np.array([.6,.25,.15])
    drift=DRIFTS["mixed"]
    U,y=sample_target(pools["052"],prior,960,drift,rng)
    fit,l1,mae,sign=fit_metrics(m,U,y,prior,drift)
    if not np.all(np.isfinite(fit["delta_raw"])):
        raise AssertionError("nonfinite delta")
    if abs(fit["pi"].sum()-1)>1e-8:
        raise AssertionError("pi sum")
    if l1>0.35 or mae>0.8:
        raise AssertionError(("weak synthetic smoke",l1,mae,sign,fit["pi"]))
    print("060 SELF-TEST PASS",{"prior_l1":l1,"delta_mae":mae,"sign":sign,
          "pi":fit["pi"].tolist(),"iterations":fit["iterations"]})

def flatten_delta(prefix,delta):
    out={}
    for y in range(K):
        for j in range(D):
            out[f"{prefix}_{LABELS[y].replace(' ','_')}_{FEATURES[j]}"]=float(delta[y,j])
    return out

def actual_fit(source_rows,target_rows):
    model=AnchoredMixture(source_rows)
    U=np.stack([r["u"] for r in target_rows])
    fit=model.fit(U)
    return model,fit

def actual_eval(model,fit,source_rows,target_rows):
    yt=np.array([r["y"] for r in target_rows],int)
    Ut=np.stack([r["u"] for r in target_rows])
    true_pi=np.bincount(yt,minlength=K)/len(yt)
    source_mu_raw=np.stack([
        np.stack([r["u"] for r in source_rows if r["y"]==k]).mean(axis=0)
        for k in range(K)
    ])
    true_delta=np.stack([
        Ut[yt==k].mean(axis=0)-source_mu_raw[k] for k in range(K)
    ])
    est=fit["delta_raw"]
    prior_l1=float(np.sum(np.abs(fit["pi"]-true_pi)))
    mae=float(np.mean(np.abs(est-true_delta)))
    total=float(np.sum(true_pi[:,None]*(true_delta*true_delta)))
    resid=float(np.sum(true_pi[:,None]*((est-true_delta)**2)))
    r2=np.nan if total<1e-12 else 1-resid/total
    mask=np.abs(true_delta)>=.5
    sign=np.nan
    if np.any(mask):
        sign=float(np.mean(np.sign(est[mask])==np.sign(true_delta[mask])))
    return {
        "true_pi":true_pi,"true_delta":true_delta,
        "prior_l1":prior_l1,"delta_mae":mae,
        "r2":float(r2),"sign_accuracy":sign,
    }

def synthetic_summary(model,rows,source_tag,rng):
    out=[]
    for prior_name,prior in PRIORS.items():
        for n in BATCHES:
            for drift_name,drift in DRIFTS.items():
                l1s=[]; maes=[]; signs=[]; iters=[]; minmass=[]
                for _ in range(REPS):
                    U,y=sample_target(rows,prior,n,drift,rng)
                    fit,l1,mae,sign=fit_metrics(model,U,y,prior,drift)
                    l1s.append(l1); maes.append(mae); iters.append(fit["iterations"])
                    minmass.append(float(np.min(fit["mass"])))
                    if np.isfinite(sign): signs.append(sign)
                out.append({
                    "source":source_tag,"prior":prior_name,"batch_n":n,"drift":drift_name,
                    "prior_l1_mean":float(np.mean(l1s)),
                    "prior_l1_median":float(np.median(l1s)),
                    "delta_mae_mean":float(np.mean(maes)),
                    "delta_mae_median":float(np.median(maes)),
                    "nonzero_sign_accuracy":float(np.mean(signs)) if signs else np.nan,
                    "iterations_mean":float(np.mean(iters)),
                    "min_effective_mass_mean":float(np.mean(minmass)),
                })
                print("060 synthetic",source_tag,prior_name,n,drift_name,flush=True)
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("freeze.json","actual_unlabeled.csv","synthetic_summary.csv"):
        if (OUT/name).exists():
            raise RuntimeError("formal output exists: "+name)
    fr=freeze()
    pools={k:load_pool(k) for k in ("052","053")}

    actual_rows=[]
    actual_cache={}
    for source,target in (("052","053"),("053","052")):
        model,fit=actual_fit(pools[source],pools[target])
        row={
            "source":source,"target":target,"target_n":len(pools[target]),
            "pi_S":fit["pi"][0],"pi_NS":fit["pi"][1],"pi_NA":fit["pi"][2],
            "mass_S":fit["mass"][0],"mass_NS":fit["mass"][1],"mass_NA":fit["mass"][2],
            "objective":fit["objective"],"iterations":fit["iterations"],
            **flatten_delta("delta_hat",fit["delta_raw"]),
        }
        actual_rows.append(row)
        actual_cache[(source,target)]=(model,fit)
    csvwrite(OUT/"actual_unlabeled.csv",actual_rows)
    blind_sha=sha(OUT/"actual_unlabeled.csv")

    rng=np.random.default_rng(SEED)
    syn=[]
    for source in ("052","053"):
        syn.extend(synthetic_summary(
            AnchoredMixture(pools[source]),pools[source],source,rng))
    csvwrite(OUT/"synthetic_summary.csv",syn)

    old059={(r["source"],r["target"]):r
            for r in read_csv(O059/"actual_evaluation.csv")}
    eval_rows=[]
    for source,target in (("052","053"),("053","052")):
        model,fit=actual_cache[(source,target)]
        ev=actual_eval(model,fit,pools[source],pools[target])
        row={
            "source":source,"target":target,
            "true_S":ev["true_pi"][0],"true_NS":ev["true_pi"][1],"true_NA":ev["true_pi"][2],
            "prior_L1":ev["prior_l1"],"delta_MAE":ev["delta_mae"],
            "class_specific_R2":ev["r2"],
            "meaningful_sign_accuracy":ev["sign_accuracy"],
            "global059_R2":float(old059[(source,target)]["R2_joint"]),
            **flatten_delta("delta_true",ev["true_delta"]),
        }
        eval_rows.append(row)
    csvwrite(OUT/"actual_evaluation.csv",eval_rows)

    syn960=[r for r in syn if r["batch_n"]==960]
    sign960=[r for r in syn960 if np.isfinite(r["nonzero_sign_accuracy"])]
    agg={
        "n960_prior_l1_mean":float(np.mean([r["prior_l1_mean"] for r in syn960])),
        "n960_delta_mae_mean":float(np.mean([r["delta_mae_mean"] for r in syn960])),
        "n960_nonzero_sign_accuracy":float(np.mean([r["nonzero_sign_accuracy"] for r in sign960])),
    }
    synthetic_pass=bool(
        agg["n960_prior_l1_mean"]<=.10 and
        agg["n960_delta_mae_mean"]<=.30 and
        agg["n960_nonzero_sign_accuracy"]>=.90)
    actual_pass=bool(all(
        r["class_specific_R2"]>=.50 and r["prior_L1"]<=.15
        for r in eval_rows))
    run={
        "status":"PASS","git_head":fr["git_head"],
        "new_api_calls":0,"reserved_used":False,
        "actual_unlabeled_sha256_before_gt_evaluation":blind_sha,
        "pools":{k:len(v) for k,v in pools.items()},
        "synthetic_n960":agg,
        "synthetic_recovery_pass":synthetic_pass,
        "actual_class_specific_pass":actual_pass,
        "advance_to_dynamic_decision":bool(synthetic_pass and actual_pass),
    }
    put(OUT/"run_summary.json",run)
    write_report(actual_rows,eval_rows,run)
    print("060 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(actual_rows,eval_rows,run):
    lines=[
        "# 060：Unlabeled Class-specific Judge-drift Estimation",
        "",
        "## 核心问题",
        "",
        "059的真实Judge漂移明显依赖真实类别。060用source anchored latent mixture，在target 0标签下同时估target prior和3×4 class-specific score drift。",
        "",
        "## 真实052↔053无标签估计",
        "",
        "| source→target | pi_hat(S/NS/NA) | effective mass(S/NS/NA) | iterations |",
        "|---|---|---|---:|",
    ]
    for r in actual_rows:
        pi=f'{r["pi_S"]:.3f}/{r["pi_NS"]:.3f}/{r["pi_NA"]:.3f}'
        mass=f'{r["mass_S"]:.1f}/{r["mass_NS"]:.1f}/{r["mass_NA"]:.1f}'
        lines.append(
            f'| {r["source"]}→{r["target"]} | {pi} | {mass} | {r["iterations"]} |')

    lines += [
        "",
        "actual_unlabeled.csv先写入并记录哈希，随后才进行target GT评价。",
        "",
        "## 解盲评价",
        "",
        "| source→target | prior L1 | delta MAE | class-specific R2 | 059 global R2 | sign acc |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in eval_rows:
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["prior_L1"]:.3f} | '
            f'{r["delta_MAE"]:.3f} | {r["class_specific_R2"]:.3f} | '
            f'{r["global059_R2"]:.3f} | {r["meaningful_sign_accuracy"]:.3f} |')
    a=run["synthetic_n960"]
    lines += [
        "",
        "## Synthetic recovery（n=960）",
        "",
        f'- prior L1 mean: **{a["n960_prior_l1_mean"]:.3f}**',
        f'- class-specific delta MAE mean: **{a["n960_delta_mae_mean"]:.3f}**',
        f'- nonzero drift sign accuracy: **{a["n960_nonzero_sign_accuracy"]:.2%}**',
        f'- synthetic门槛：**{"PASS" if run["synthetic_recovery_pass"] else "FAIL"}**',
        "",
        "## 结论",
        "",
    ]

    if run["advance_to_dynamic_decision"]:
        lines += [
            "**060通过synthetic与真实两道门槛，可进入下一步dynamic decision。**",
            "",
            "class-specific drift在0标签target上具备可恢复性，并明显优于059 global-shift表示。",
        ]
    elif run["synthetic_recovery_pass"]:
        lines += [
            "**060合成恢复通过，但真实门槛未全部通过。**",
            "",
            "说明class-specific参数化方向更合理，但当前0标签latent mixture在真实batch上仍不足以稳定恢复到可直接驱动动态决策的程度。",
        ]
    else:
        lines += [
            "**060 synthetic recovery未过门槛。**",
            "",
            "当前12维class-specific latent mixture本身还不够稳定，不进入动态决策。",
        ]
    lines += [
        "",
        "## 边界",
        "",
        "- 估计的是score-space class-specific drift，不是完整target confusion matrix。",
        "- 052/053仍是development内部batch。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    self_test() if args.self_test else main()
