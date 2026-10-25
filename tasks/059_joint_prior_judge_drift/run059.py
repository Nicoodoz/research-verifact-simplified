from pathlib import Path
import argparse, csv, hashlib, json, subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/059_joint_prior_judge_drift"
O055 = ROOT / "outputs/055_zero_label_policy_adaptation"
LABELS = ["Supported","Not Supported","Not Addressed"]
K = 3
EPS = 0.5
GRID_STEP = 0.01
REPS = 200
SEED = 20260922059
PRIORS = {
    "source": np.array([1108.,100.,170.]) / 1378.,
    "S60": np.array([.60,.20,.20]),
    "NS_heavy": np.array([.60,.30,.10]),
    "NA_heavy": np.array([.60,.10,.30]),
}
BATCHES = (240,480,960)
DRIFTS = {
    "none": np.array([0.,0.,0.,0.]),
    "DS_S_up": np.array([.5,0.,0.,0.]),
    "DS_S_down": np.array([-.5,0.,0.,0.]),
    "DS_NS_up": np.array([0.,.5,0.,0.]),
    "DS_NS_down": np.array([0.,-.5,0.,0.]),
    "Q_S_up": np.array([0.,0.,.5,0.]),
    "Q_S_down": np.array([0.,0.,-.5,0.]),
    "Q_NS_up": np.array([0.,0.,0.,.5]),
    "Q_NS_down": np.array([0.,0.,0.,-.5]),
    "conflict": np.array([.5,0.,-.5,0.]),
}
UT = np.triu_indices(4)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]

def csvwrite(path, rows):
    rows=list(rows)
    fields=list(dict.fromkeys(k for r in rows for k in r))
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
            "id":x["id"],"sid":str(x["sid"]),"y":LABELS.index(x["GT"]),
            "u":np.r_[scores_u(x["ts_scores"]),scores_u(x["qwen_scores"])]
        })
    return out

def simplex_grid(step=GRID_STEP):
    m=int(round(1/step))
    out=[]
    for i in range(m+1):
        for j in range(m+1-i):
            k=m-i-j
            out.append([i/m,j/m,k/m])
    return np.asarray(out,float)

class MomentModel:
    def __init__(self, rows):
        self.U=np.stack([r["u"] for r in rows])
        self.y=np.array([r["y"] for r in rows],int)
        self.mean=self.U.mean(axis=0)
        self.std=self.U.std(axis=0)
        self.std[self.std<1e-8]=1.0
        Z=(self.U-self.mean)/self.std
        self.mu_raw=np.stack([self.U[self.y==k].mean(axis=0) for k in range(K)])
        self.mu_z=np.stack([Z[self.y==k].mean(axis=0) for k in range(K)])
        self.cov_z=[]
        for k in range(K):
            zz=Z[self.y==k]
            c=np.cov(zz,rowvar=False,bias=True)
            self.cov_z.append(c)
        self.cov_z=np.stack(self.cov_z)
        self.second_z=self.cov_z+np.einsum("ki,kj->kij",self.mu_z,self.mu_z)
        self.grid=simplex_grid()
        self.grid_cov=self._grid_cov(self.grid)
        self.grid_vec=self.grid_cov[:,UT[0],UT[1]]
        self.grid_norm=np.sum(self.grid_vec*self.grid_vec,axis=1)

    def _grid_cov(self,P):
        means=P@self.mu_z
        second=np.einsum("pk,kij->pij",P,self.second_z)
        return second-np.einsum("pi,pj->pij",means,means)

    def estimate_pi_covs(self,covs_raw):
        C=np.asarray(covs_raw,float)/(self.std[None,:,None]*self.std[None,None,:])
        V=C[:,UT[0],UT[1]]
        vnorm=np.sum(V*V,axis=1)[:,None]
        dist=vnorm+self.grid_norm[None,:]-2*(V@self.grid_vec.T)
        idx=np.argmin(dist,axis=1)
        return self.grid[idx],np.sqrt(np.maximum(dist[np.arange(len(idx)),idx],0))

    def estimate_one(self,Utarget):
        Utarget=np.asarray(Utarget,float)
        cov=np.cov(Utarget,rowvar=False,bias=True)[None,:,:]
        p,fit=self.estimate_pi_covs(cov)
        theta=Utarget.mean(axis=0)-p[0]@self.mu_raw
        return p[0],theta,float(fit[0])

def alloc(prior,n):
    x=np.asarray(prior)*n
    base=np.floor(x).astype(int)
    left=int(n-base.sum())
    order=np.argsort(-(x-base),kind="stable")
    for i in order[:left]: base[i]+=1
    return base

def sample_counts(rows,prior,n,reps,rng):
    y=np.array([r["y"] for r in rows],int)
    by=[np.where(y==k)[0] for k in range(K)]
    counts=np.zeros((reps,len(rows)),float)
    for k,c in enumerate(alloc(prior,n)):
        probs=np.full(len(by[k]),1/len(by[k]))
        draws=rng.multinomial(int(c),probs,size=reps)
        counts[:,by[k]]=draws
    return counts

def sampled_moments(model,counts,n):
    U=model.U
    mean=(counts@U)/n
    outer=np.einsum("ni,nj->nij",U,U).reshape(len(U),-1)
    second=(counts@outer)/n
    cov=second.reshape(len(counts),4,4)-np.einsum("ri,rj->rij",mean,mean)
    return mean,cov

def synthetic_for(model,rows,prior,n,rng):
    counts=sample_counts(rows,prior,n,REPS,rng)
    mean,cov=sampled_moments(model,counts,n)
    p_hat,fit=model.estimate_pi_covs(cov)
    prior_l1=np.sum(np.abs(p_hat-prior[None,:]),axis=1)
    out=[]
    for name,theta_true in DRIFTS.items():
        theta_hat=mean+theta_true[None,:]-p_hat@model.mu_raw
        err=theta_hat-theta_true[None,:]
        nz=np.where(np.abs(theta_true)>1e-12)[0]
        sign_acc=np.nan
        if len(nz):
            sign_acc=float(np.mean(np.sign(theta_hat[:,nz])==np.sign(theta_true[nz])[None,:]))
        out.append({
            "drift":name,
            "prior_l1_mean":float(prior_l1.mean()),
            "prior_l1_median":float(np.median(prior_l1)),
            "theta_mae_mean":float(np.mean(np.abs(err))),
            "theta_rmse":float(np.sqrt(np.mean(err*err))),
            "nonzero_sign_accuracy":sign_acc,
            "cov_fit_mean":float(fit.mean()),
        })
    return out

def actual_unlabeled(source_rows,target_rows):
    m=MomentModel(source_rows)
    U=np.stack([r["u"] for r in target_rows])
    p,theta,fit=m.estimate_one(U)
    return m,p,theta,fit

def actual_evaluation(model,source_rows,target_rows,p_hat,theta_hat):
    yt=np.array([r["y"] for r in target_rows],int)
    true=np.bincount(yt,minlength=K)/len(yt)
    Ut=np.stack([r["u"] for r in target_rows])
    theta_oracle=Ut.mean(axis=0)-true@model.mu_raw
    delta=[]
    for k in range(K):
        mu_t=Ut[yt==k].mean(axis=0)
        delta.append(mu_t-model.mu_raw[k])
    delta=np.stack(delta)
    resid=delta-theta_oracle[None,:]
    total=float(np.sum(true[:,None]*(delta*delta)))
    residual=float(np.sum(true[:,None]*(resid*resid)))
    r2=np.nan if total<1e-12 else 1-residual/total
    def r2_slice(sl):
        d=delta[:,sl]; th=theta_oracle[sl]; rr=d-th[None,:]
        tt=float(np.sum(true[:,None]*(d*d)))
        ee=float(np.sum(true[:,None]*(rr*rr)))
        return np.nan if tt<1e-12 else 1-ee/tt
    return {
        "true_pi":true,
        "prior_l1":float(np.sum(np.abs(p_hat-true))),
        "theta_oracle":theta_oracle,
        "theta_abs_error":np.abs(theta_hat-theta_oracle),
        "theta_mae":float(np.mean(np.abs(theta_hat-theta_oracle))),
        "delta_y":delta,
        "r2_joint":float(r2),
        "r2_ds":float(r2_slice(slice(0,2))),
        "r2_qwen":float(r2_slice(slice(2,4))),
    }

def freeze():
    inputs={
        "features_qwen_052":O055/"features_qwen_052.jsonl",
        "features_qwen_053":O055/"features_qwen_053.jsonl",
        "protocol":ROOT/"tasks/059_joint_prior_judge_drift/protocol.md",
    }
    obj={
        "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"eps_score":EPS,"grid_step":GRID_STEP,"reps":REPS,
        "priors":{k:v.tolist() for k,v in PRIORS.items()},
        "batches":list(BATCHES),
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
    m=MomentModel(pools["052"])
    if m.grid.shape[0]!=5151: raise AssertionError(m.grid.shape)
    p=np.array([.6,.25,.15])
    cov_z=m._grid_cov(p[None,:])[0]
    cov_raw=cov_z*(m.std[:,None]*m.std[None,:])
    ph,fit=m.estimate_pi_covs(cov_raw[None,:,:])
    if np.max(np.abs(ph[0]-p))>0.011:
        raise AssertionError(("pi recovery",ph[0],p))
    th=np.array([.5,-.5,.25,-.25])
    U=m.U+th
    ph2,th2,fit2=m.estimate_one(U)
    # source empirical covariance corresponds to empirical source prior, not fixed PRIORS["source"].
    emp=np.bincount(m.y,minlength=K)/len(m.y)
    if np.sum(np.abs(ph2-emp))>0.08:
        raise AssertionError(("emp prior",ph2,emp))
    if np.mean(np.abs(th2-th))>0.15:
        raise AssertionError(("theta",th2,th))
    print("059 SELF-TEST PASS", {k:len(v) for k,v in pools.items()},
          "grid",len(m.grid))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("freeze.json","actual_unlabeled.csv","synthetic_summary.csv"):
        if (OUT/name).exists(): raise RuntimeError("formal output exists: "+name)
    fr=freeze()
    pools={k:load_pool(k) for k in ("052","053")}
    rng=np.random.default_rng(SEED)

    actual_rows=[]
    actual_cache={}
    for source,target in (("052","053"),("053","052")):
        model,p,theta,fit=actual_unlabeled(pools[source],pools[target])
        row={
            "source":source,"target":target,"target_n":len(pools[target]),
            "pi_S":p[0],"pi_NS":p[1],"pi_NA":p[2],
            "theta_DS_S":theta[0],"theta_DS_NS":theta[1],
            "theta_Q_S":theta[2],"theta_Q_NS":theta[3],
            "cov_fit":fit,
        }
        actual_rows.append(row)
        actual_cache[(source,target)]=(model,p,theta,fit)
    csvwrite(OUT/"actual_unlabeled.csv",actual_rows)
    blind_sha=sha(OUT/"actual_unlabeled.csv")

    syn=[]
    for source in ("052","053"):
        model=MomentModel(pools[source])
        for prior_name,prior in PRIORS.items():
            for n in BATCHES:
                base=synthetic_for(model,pools[source],prior,n,rng)
                for z in base:
                    syn.append({
                        "source":source,"prior":prior_name,"batch_n":n,**z
                    })
                print("059 synthetic",source,prior_name,n,flush=True)
    csvwrite(OUT/"synthetic_summary.csv",syn)

    actual_eval=[]
    for source,target in (("052","053"),("053","052")):
        model,p,theta,fit=actual_cache[(source,target)]
        ev=actual_evaluation(model,pools[source],pools[target],p,theta)
        d=ev["delta_y"]
        to=ev["theta_oracle"]
        te=ev["theta_abs_error"]
        actual_eval.append({
            "source":source,"target":target,
            "true_S":ev["true_pi"][0],"true_NS":ev["true_pi"][1],"true_NA":ev["true_pi"][2],
            "prior_L1":ev["prior_l1"],
            "theta_oracle_DS_S":to[0],"theta_oracle_DS_NS":to[1],
            "theta_oracle_Q_S":to[2],"theta_oracle_Q_NS":to[3],
            "theta_MAE":ev["theta_mae"],
            "theta_abs_err_DS_S":te[0],"theta_abs_err_DS_NS":te[1],
            "theta_abs_err_Q_S":te[2],"theta_abs_err_Q_NS":te[3],
            "R2_joint":ev["r2_joint"],"R2_DS":ev["r2_ds"],"R2_Qwen":ev["r2_qwen"],
            "delta_S_true_DS_S":d[0,0],"delta_NS_true_DS_S":d[1,0],"delta_NA_true_DS_S":d[2,0],
            "delta_S_true_DS_NS":d[0,1],"delta_NS_true_DS_NS":d[1,1],"delta_NA_true_DS_NS":d[2,1],
            "delta_S_true_Q_S":d[0,2],"delta_NS_true_Q_S":d[1,2],"delta_NA_true_Q_S":d[2,2],
            "delta_S_true_Q_NS":d[0,3],"delta_NS_true_Q_NS":d[1,3],"delta_NA_true_Q_NS":d[2,3],
        })
    csvwrite(OUT/"actual_evaluation.csv",actual_eval)

    syn960=[r for r in syn if r["batch_n"]==960]
    nonzero=[r for r in syn960 if not np.isnan(r["nonzero_sign_accuracy"])]
    agg={
        "n960_prior_l1_mean":float(np.mean([r["prior_l1_mean"] for r in syn960])),
        "n960_theta_mae_mean":float(np.mean([r["theta_mae_mean"] for r in syn960])),
        "n960_nonzero_sign_accuracy":float(np.mean([r["nonzero_sign_accuracy"] for r in nonzero])),
    }
    synthetic_pass=bool(
        agg["n960_prior_l1_mean"]<=.10 and
        agg["n960_theta_mae_mean"]<=.15 and
        agg["n960_nonzero_sign_accuracy"]>=.90
    )
    actual_r2_pass=bool(all(r["R2_joint"]>=.50 for r in actual_eval))
    advance=bool(synthetic_pass and actual_r2_pass)
    run={
        "status":"PASS","git_head":fr["git_head"],"new_api_calls":0,"reserved_used":False,
        "actual_unlabeled_sha256_before_gt_evaluation":blind_sha,
        "pools":{k:len(v) for k,v in pools.items()},
        "synthetic_n960":agg,
        "synthetic_recovery_pass":synthetic_pass,
        "actual_common_shift_r2_pass":actual_r2_pass,
        "advance_to_060":advance,
    }
    put(OUT/"run_summary.json",run)
    write_report(actual_rows,actual_eval,syn,run)
    print("059 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(actual_rows,actual_eval,syn,run):
    lines=[
        "# 059：Joint Prior and Judge-drift Estimation","",
        "## 目标","",
        "target无GT时，同时估类别比例与每个Judge的两个全局log-odds漂移参数：S偏移、NS相对NA偏移。","",
        "prior由联合DeepSeek+Qwen 4维log-odds协方差估计；全局additive bias不改变协方差。随后用target均值减去source类条件均值按估计prior的混合值得到theta。","",
        "## 真实052↔053无标签估计","",
        "| source→target | pi_hat(S/NS/NA) | DS θS | DS θNS | Q θS | Q θNS |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for r in actual_rows:
        pi=f'{r["pi_S"]:.3f}/{r["pi_NS"]:.3f}/{r["pi_NA"]:.3f}'
        lines.append(f'| {r["source"]}→{r["target"]} | {pi} | {r["theta_DS_S"]:+.3f} | {r["theta_DS_NS"]:+.3f} | {r["theta_Q_S"]:+.3f} | {r["theta_Q_NS"]:+.3f} |')
    lines += [
        "",
        "上述结果在GT评价前先写入actual_unlabeled.csv并记录哈希。",
        "",
        "## 解盲评价","",
        "| source→target | prior L1 | theta MAE vs oracle | R2 joint | R2 DS | R2 Qwen |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in actual_eval:
        lines.append(f'| {r["source"]}→{r["target"]} | {r["prior_L1"]:.3f} | {r["theta_MAE"]:.3f} | {r["R2_joint"]:.3f} | {r["R2_DS"]:.3f} | {r["R2_Qwen"]:.3f} |')
    a=run["synthetic_n960"]
    lines += [
        "",
        "## Synthetic recovery（n=960汇总）","",
        f'- prior L1 mean: **{a["n960_prior_l1_mean"]:.3f}**',
        f'- theta MAE mean: **{a["n960_theta_mae_mean"]:.3f}**',
        f'- 非零drift sign accuracy: **{a["n960_nonzero_sign_accuracy"]:.3%}**',
        f'- 事前synthetic门槛：**{"PASS" if run["synthetic_recovery_pass"] else "FAIL"}**',
        "",
        "## 结论","",
    ]
    if run["advance_to_060"]:
        lines += [
            "**059通过synthetic recovery与真实common-shift adequacy两道门槛，可进入060。**",
            "",
            "当前4参数全局Judge drift在无标签target中可估，并能解释真实跨batch类条件均值变化的主要部分。",
        ]
    elif run["synthetic_recovery_pass"]:
        lines += [
            "**059在合成已知漂移上可恢复，但真实common-shift假设不足。**",
            "",
            "说明估计器本身可工作，但真实Judge变化不是简单的每个Judge两个全局bias；不应直接把这4个参数送入060。",
        ]
    else:
        lines += [
            "**059 synthetic recovery未过门槛。**",
            "",
            "当前covariance→prior→mean residual分解本身还不足以可靠恢复Judge drift，不进入060。",
        ]
    lines += [
        "",
        "## 边界","",
        "- theta描述score-space全局bias，不是完整confusion matrix或class-specific recall。",
        "- 052/053为development内部batch。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    self_test() if args.self_test else main()
