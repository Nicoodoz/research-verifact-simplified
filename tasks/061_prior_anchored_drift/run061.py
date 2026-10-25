from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, math, subprocess
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/061_prior_anchored_drift"
O055 = ROOT / "outputs/055_zero_label_policy_adaptation"
O060 = ROOT / "outputs/060_class_specific_drift"
P060 = ROOT / "tasks/060_class_specific_drift/run060.py"

spec = importlib.util.spec_from_file_location("r060", P060)
r060 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r060)

LABELS = r060.LABELS
K, D = 3, 4
REPS = 30
SEED = 20260922061
BATCHES = r060.BATCHES
PRIORS = r060.PRIORS
DRIFTS = r060.DRIFTS

SOURCE_COUNTS=np.array([1108.,100.,170.])
SOURCE_PRIOR=SOURCE_COUNTS/SOURCE_COUNTS.sum()
CAL_COUNTS=np.array([48.,47.,48.])
CAL_PRIOR=CAL_COUNTS/CAL_COUNTS.sum()
G=float(json.loads(
    (ROOT/"outputs/053_thinking_prior_validation/freeze.json").read_text(
        encoding="utf-8-sig"))["calibration_theta"]["T-S"]["G"][0])
BIAS_S=G+math.log(SOURCE_PRIOR[0]/CAL_PRIOR[0])-math.log(SOURCE_PRIOR[2]/CAL_PRIOR[2])
BIAS_NS=math.log(SOURCE_PRIOR[1]/CAL_PRIOR[1])-math.log(SOURCE_PRIOR[2]/CAL_PRIOR[2])

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_jsonl(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return [json.loads(x) for x in f if x.strip()]

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def csvwrite(path,rows):
    rows=list(rows)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def put(path,obj):
    Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")

def load_pool(tag,include_gt=True):
    out=[]
    for x in read_jsonl(O055/f"features_qwen_{tag}.jsonl"):
        s=x["ts_scores"]
        z=np.log(np.maximum(
            np.array([float(s[k])/100 for k in LABELS],float),1e-6))
        rel=np.array([z[0]-z[2],z[1]-z[2]],float)
        row={
            "id":x["id"],"sid":str(x["sid"]),
            "u":np.r_[r060.scores_u(x["ts_scores"]),
                       r060.scores_u(x["qwen_scores"])],
            "ds_rel":rel,
        }
        if include_gt:
            row["y"]=LABELS.index(x["GT"])
        out.append(row)
    return out

def ds_hard(rel):
    rel=np.asarray(rel,float)
    vals=np.c_[rel[:,0]+BIAS_S,rel[:,1]+BIAS_NS,np.zeros(len(rel))]
    return np.argmax(vals,axis=1)

class SimplexLS:
    def __init__(self,C):
        self.C=np.asarray(C,float)
        self.solvers=[]
        for mask in range(1,1<<K):
            idx=[i for i in range(K) if mask&(1<<i)]
            A=self.C[:,idx]
            H=2*(A.T@A)
            one=np.ones((len(idx),1))
            M=np.block([[H,one],[one.T,np.zeros((1,1))]])
            self.solvers.append((idx,A,np.linalg.pinv(M)))
    def solve(self,q):
        q=np.asarray(q,float)
        best=None
        for idx,A,pinv in self.solvers:
            rhs=np.r_[2*(A.T@q),1.0]
            x=pinv@rhs
            psub=x[:-1]
            if np.min(psub)<-1e-9:
                continue
            p=np.zeros(K); p[idx]=np.maximum(psub,0); p/=p.sum()
            loss=float(np.sum((self.C@p-q)**2))
            if best is None or loss<best[0]:
                best=(loss,p)
        if best is None:
            raise RuntimeError("simplex LS failed")
        return best[1]

def source_confusion(rows):
    y=np.array([r["y"] for r in rows],int)
    rel=np.stack([r["ds_rel"] for r in rows])
    pred=ds_hard(rel)
    C=np.zeros((K,K),float)
    for yy,pp in zip(y,pred):
        C[pp,yy]+=1
    C/=C.sum(axis=0,keepdims=True)
    return C

def bbse_prior(source_rows,target_rel):
    C=source_confusion(source_rows)
    pred=ds_hard(target_rel)
    q=np.bincount(pred,minlength=K)/len(pred)
    return SimplexLS(C).solve(q)

def _fit_fixed_start(model,Z,pi,delta0):
    pi=np.asarray(pi,float)
    pi=np.maximum(pi,1e-8); pi/=pi.sum()
    delta=np.asarray(delta0,float).copy()
    prev=-np.inf
    eye=np.eye(D)
    for it in range(r060.MAX_ITER):
        L=model._log_components(Z,pi,delta)
        m=L.max(axis=1)
        E=np.exp(L-m[:,None])
        R=E/E.sum(axis=1,keepdims=True)
        mass=R.sum(axis=0)+1e-12
        target_mean=(R.T@Z)/mass[:,None]
        raw=target_mean-model.mu
        g=np.average(raw,axis=0,weights=mass)
        for _ in range(8):
            nd=np.empty_like(delta)
            for k in range(K):
                A=mass[k]*model.inv[k]+r060.TAU*eye
                b=mass[k]*(model.inv[k]@raw[k])+r060.TAU*g
                nd[k]=np.linalg.solve(A,b)
            nd=np.clip(nd,-r060.CLIP,r060.CLIP)
            ng=nd.mean(axis=0)
            delta=nd
            if np.max(np.abs(ng-g))<1e-8:
                g=ng
                break
            g=ng
        obj=model._objective(Z,pi,delta)
        if abs(obj-prev)<r060.TOL:
            break
        prev=obj
    return {
        "pi":pi,"delta_z":delta,
        "delta_raw":delta*model.std[None,:],
        "mass":mass,"objective":float(obj),"iterations":it+1,
    }

def fit_fixed(model,Uraw,pi):
    Z=model.transform(Uraw)
    pi=np.asarray(pi,float); pi=np.maximum(pi,1e-8); pi/=pi.sum()
    shared=Z.mean(axis=0)-pi@model.mu
    starts=[np.zeros((K,D)),np.tile(shared,(K,1))]
    fits=[_fit_fixed_start(model,Z,pi,d0) for d0 in starts]
    return max(fits,key=lambda x:x["objective"])

def sample_target(rows,prior,n,drift,rng):
    y=np.array([r["y"] for r in rows],int)
    by=[np.where(y==k)[0] for k in range(K)]
    idx=[]
    for k,c in enumerate(r060.alloc(prior,n)):
        idx.extend(rng.choice(by[k],size=int(c),replace=True).tolist())
    rng.shuffle(idx)
    yy=y[idx]
    U=np.stack([rows[i]["u"] for i in idx])+drift[yy]
    rel=np.stack([rows[i]["ds_rel"] for i in idx])+drift[yy,:2]
    return U,yy,rel

def true_delta_from_samples(model,U,yy):
    Z=model.transform(U)
    delta_z=np.stack([
        Z[yy==k].mean(axis=0)-model.mu[k] for k in range(K)
    ])
    return delta_z*model.std[None,:]

def fit_quality(fit,true_prior,true_delta):
    prior_l1=float(np.sum(np.abs(fit["pi"]-true_prior)))
    err=fit["delta_raw"]-true_delta
    mae=float(np.mean(np.abs(err)))
    nz=np.abs(true_delta)>=1e-12
    sign=np.nan
    if np.any(nz):
        sign=float(np.mean(
            np.sign(fit["delta_raw"][nz])==np.sign(true_delta[nz])))
    weights=np.asarray(true_prior,float)
    total=float(np.sum(weights[:,None]*(true_delta*true_delta)))
    resid=float(np.sum(weights[:,None]*(err*err)))
    r2=np.nan if total<1e-12 else 1-resid/total
    return prior_l1,mae,sign,float(r2)

def synthetic_condition(model,source_rows,prior,n,drift,rng):
    out={"oracle":[],"bbse":[]}
    for _ in range(REPS):
        U,yy,rel=sample_target(source_rows,prior,n,drift,rng)
        true_delta=drift
        for mode,pi in (
            ("oracle",prior),
            ("bbse",bbse_prior(source_rows,rel)),
        ):
            fit=fit_fixed(model,U,pi)
            l1,mae,sign,r2=fit_quality(fit,prior,true_delta)
            out[mode].append((l1,mae,sign,r2))
    rows=[]
    for mode,vals in out.items():
        A=np.asarray([[v[0],v[1],v[3]] for v in vals],float)
        signs=[v[2] for v in vals if np.isfinite(v[2])]
        rows.append({
            "mode":mode,
            "prior_l1_mean":float(A[:,0].mean()),
            "delta_mae_mean":float(A[:,1].mean()),
            "delta_r2_mean":float(A[:,2].mean()),
            "nonzero_sign_accuracy":
                float(np.mean(signs)) if signs else np.nan,
        })
    return rows

def flatten_delta(prefix,delta):
    out={}
    for y in range(K):
        yname=LABELS[y].replace(" ","_")
        for j,f in enumerate(r060.FEATURES):
            out[f"{prefix}_{yname}_{f}"]=float(delta[y,j])
    return out

def actual_inputs(rows):
    U=np.stack([r["u"] for r in rows])
    rel=np.stack([r["ds_rel"] for r in rows])
    y=np.array([r["y"] for r in rows],int)
    return U,rel,y

def actual_eval(model,fit,U,y,true_pi):
    true_delta=true_delta_from_samples(model,U,y)
    l1,mae,sign,r2=fit_quality(fit,true_pi,true_delta)
    return {
        "prior_l1":l1,"delta_mae":mae,
        "sign_accuracy":sign,"r2":r2,
        "true_delta":true_delta,
    }

def freeze():
    inputs={
        "features_qwen_052":O055/"features_qwen_052.jsonl",
        "features_qwen_053":O055/"features_qwen_053.jsonl",
        "run060":P060,
        "actual060":O060/"actual_evaluation.csv",
        "protocol":ROOT/"tasks/061_prior_anchored_drift/protocol.md",
    }
    obj={
        "git_head":subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"reps":REPS,
        "batches":list(BATCHES),
        "priors":{k:v.tolist() for k,v in PRIORS.items()},
        "drifts":{k:v.tolist() for k,v in DRIFTS.items()},
        "G":G,
        "bias_s":BIAS_S,"bias_ns":BIAS_NS,
        "code_sha256":sha(Path(__file__)),
        "inputs":{
            k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)}
            for k,v in inputs.items()
        },
    }
    put(OUT/"freeze.json",obj)
    return obj

def self_test():
    pools={k:load_pool(k) for k in ("052","053")}
    if len(pools["052"])!=236 or len(pools["053"])!=237:
        raise AssertionError("pool sizes")
    for source,target,expected in (
        ("052","053",np.array([0.8164057926575019,0.06417253412579169,0.11942167321670646])),
        ("053","052",np.array([0.7847781047555688,0.0682685319625071,0.1469533632874745])),
    ):
        _,rel,_=actual_inputs(pools[target])
        p=bbse_prior(pools[source],rel)
        if np.max(np.abs(p-expected))>1e-6:
            raise AssertionError(("BBSE mismatch",source,target,p,expected))
    model=r060.AnchoredMixture(pools["052"])
    rng=np.random.default_rng(7)
    prior=np.array([.6,.25,.15])
    drift=DRIFTS["mixed"]
    U,y,rel=sample_target(pools["052"],prior,960,drift,rng)
    fo=fit_fixed(model,U,prior)
    po=fit_quality(fo,prior,drift)
    pb=bbse_prior(pools["052"],rel)
    fb=fit_fixed(model,U,pb)
    qb=fit_quality(fb,prior,drift)
    if po[1]>0.8 or qb[1]>1.0:
        raise AssertionError(("weak fixed-prior smoke",po,qb,pb))
    print("061 SELF-TEST PASS",{
        "oracle_delta_mae":po[1],
        "bbse_prior_l1":qb[0],
        "bbse_delta_mae":qb[1],
    })

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("freeze.json","actual_unlabeled.csv","synthetic_summary.csv"):
        if (OUT/name).exists():
            raise RuntimeError("formal output exists: "+name)
    fr=freeze()
    source_pools={k:load_pool(k,True) for k in ("052","053")}

    # GT-blind actual BBSE-fixed fits first.
    actual_rows=[]
    blind_cache={}
    for source,target in (("052","053"),("053","052")):
        target_blind=load_pool(target,False)
        U=np.stack([r["u"] for r in target_blind])
        rel=np.stack([r["ds_rel"] for r in target_blind])
        model=r060.AnchoredMixture(source_pools[source])
        pbbse=bbse_prior(source_pools[source],rel)
        fit=fit_fixed(model,U,pbbse)
        actual_rows.append({
            "source":source,"target":target,"target_n":len(target_blind),
            "pi_S":pbbse[0],"pi_NS":pbbse[1],"pi_NA":pbbse[2],
            "mass_S":fit["mass"][0],"mass_NS":fit["mass"][1],
            "mass_NA":fit["mass"][2],
            "objective":fit["objective"],"iterations":fit["iterations"],
            **flatten_delta("delta_hat",fit["delta_raw"]),
        })
        blind_cache[(source,target)]=(model,U,rel,pbbse,fit)
    csvwrite(OUT/"actual_unlabeled.csv",actual_rows)
    blind_sha=sha(OUT/"actual_unlabeled.csv")

    rng=np.random.default_rng(SEED)
    syn=[]
    for source in ("052","053"):
        model=r060.AnchoredMixture(source_pools[source])
        for prior_name,prior in PRIORS.items():
            for n in BATCHES:
                for drift_name,drift in DRIFTS.items():
                    for z in synthetic_condition(
                        model,source_pools[source],prior,n,drift,rng):
                        syn.append({
                            "source":source,"prior":prior_name,
                            "batch_n":n,"drift":drift_name,**z
                        })
                    print("061 synthetic",source,prior_name,n,drift_name,flush=True)
    csvwrite(OUT/"synthetic_summary.csv",syn)

    # GT-aware diagnostics only after blind file is frozen.
    old060={(r["source"],r["target"]):r
            for r in read_csv(O060/"actual_evaluation.csv")}
    eval_rows=[]
    for source,target in (("052","053"),("053","052")):
        target_eval=load_pool(target,True)
        U=np.stack([r["u"] for r in target_eval])
        y=np.array([r["y"] for r in target_eval],int)
        true_pi=np.bincount(y,minlength=K)/len(y)
        model,_,_,pbbse,fit_bbse=blind_cache[(source,target)]
        fit_oracle=fit_fixed(model,U,true_pi)
        for mode,fit in (("bbse",fit_bbse),("oracle",fit_oracle)):
            ev=actual_eval(model,fit,U,y,true_pi)
            eval_rows.append({
                "source":source,"target":target,"mode":mode,
                "true_S":true_pi[0],"true_NS":true_pi[1],"true_NA":true_pi[2],
                "pi_S":fit["pi"][0],"pi_NS":fit["pi"][1],"pi_NA":fit["pi"][2],
                "prior_L1":ev["prior_l1"],
                "delta_MAE":ev["delta_mae"],
                "class_specific_R2":ev["r2"],
                "meaningful_sign_accuracy":ev["sign_accuracy"],
                "joint_free060_R2":float(old060[(source,target)]["class_specific_R2"]),
                **flatten_delta("delta_true",ev["true_delta"]),
            })
    csvwrite(OUT/"actual_evaluation.csv",eval_rows)

    syn960=[r for r in syn if r["batch_n"]==960]
    agg={}
    for mode in ("oracle","bbse"):
        x=[r for r in syn960 if r["mode"]==mode]
        sx=[r for r in x if np.isfinite(r["nonzero_sign_accuracy"])]
        agg[mode]={
            "prior_l1_mean":float(np.mean([r["prior_l1_mean"] for r in x])),
            "delta_mae_mean":float(np.mean([r["delta_mae_mean"] for r in x])),
            "delta_r2_mean":float(np.nanmean([r["delta_r2_mean"] for r in x])),
            "nonzero_sign_accuracy":float(np.mean(
                [r["nonzero_sign_accuracy"] for r in sx])),
        }

    oracle_actual=[r for r in eval_rows if r["mode"]=="oracle"]
    bbse_actual=[r for r in eval_rows if r["mode"]=="bbse"]
    oracle_pass=bool(
        agg["oracle"]["delta_mae_mean"]<=.30 and
        agg["oracle"]["nonzero_sign_accuracy"]>=.90 and
        all(r["class_specific_R2"]>=.50 for r in oracle_actual))
    bbse_pass=bool(
        agg["bbse"]["prior_l1_mean"]<=.10 and
        agg["bbse"]["delta_mae_mean"]<=.35 and
        agg["bbse"]["nonzero_sign_accuracy"]>=.90 and
        all(r["prior_L1"]<=.15 and r["class_specific_R2"]>=.50
            for r in bbse_actual))
    if oracle_pass and bbse_pass:
        diagnosis="fixed_prior_solves_and_bbse_is_sufficient"
    elif oracle_pass:
        diagnosis="fixed_prior_solves_but_bbse_sensor_is_bottleneck"
    else:
        diagnosis="oracle_prior_does_not_solve_class_specific_recovery"

    run={
        "status":"PASS","git_head":fr["git_head"],
        "new_api_calls":0,"reserved_used":False,
        "actual_unlabeled_sha256_before_gt_evaluation":blind_sha,
        "pools":{k:len(v) for k,v in source_pools.items()},
        "synthetic_n960":agg,
        "oracle_diagnostic_pass":oracle_pass,
        "bbse_deployable_pass":bbse_pass,
        "diagnosis":diagnosis,
        "advance_to_dynamic_decision":bool(oracle_pass and bbse_pass),
    }
    put(OUT/"run_summary.json",run)
    write_report(actual_rows,eval_rows,run)
    print("061 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(actual_rows,eval_rows,run):
    lines=[
        "# 061：Prior-Anchored Class-specific Drift Estimation","",
        "## 核心问题","",
        "061只改变060的一件事：target prior固定，不再与12维class-specific drift一起自由更新。Oracle-fixed用于诊断上限，BBSE-fixed用于0标签可部署检验。","",
        "## GT盲BBSE-fixed实际结果","",
        "| source→target | BBSE pi(S/NS/NA) | effective mass(S/NS/NA) |",
        "|---|---|---|",
    ]
    for r in actual_rows:
        pi=f'{r["pi_S"]:.3f}/{r["pi_NS"]:.3f}/{r["pi_NA"]:.3f}'
        mass=f'{r["mass_S"]:.1f}/{r["mass_NS"]:.1f}/{r["mass_NA"]:.1f}'
        lines.append(f'| {r["source"]}→{r["target"]} | {pi} | {mass} |')
    lines += [
        "",
        "actual_unlabeled.csv先写入并记录SHA256，随后才生成Oracle与GT评价。","",
        "## 解盲评价","",
        "| source→target | mode | prior L1 | delta MAE | R2 | sign acc | 060 free-prior R2 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in eval_rows:
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["mode"]} | '
            f'{r["prior_L1"]:.3f} | {r["delta_MAE"]:.3f} | '
            f'{r["class_specific_R2"]:.3f} | {r["meaningful_sign_accuracy"]:.3f} | '
            f'{r["joint_free060_R2"]:.3f} |')
    lines += ["","## Synthetic n=960",""]
    for mode in ("oracle","bbse"):
        a=run["synthetic_n960"][mode]
        lines += [
            f'### {mode}',
            f'- prior L1 mean: **{a["prior_l1_mean"]:.3f}**',
            f'- delta MAE mean: **{a["delta_mae_mean"]:.3f}**',
            f'- delta R2 mean: **{a["delta_r2_mean"]:.3f}**',
            f'- nonzero sign accuracy: **{a["nonzero_sign_accuracy"]:.2%}**',
            "",
        ]
    lines += ["## 结论",""]
    if run["diagnosis"]=="fixed_prior_solves_and_bbse_is_sufficient":
        lines += [
            "**Oracle与BBSE固定prior均通过。**",
            "",
            "060的主要问题就是prior-drift confounding；当前zero-label分解具备进入动态decision的依据。",
        ]
    elif run["diagnosis"]=="fixed_prior_solves_but_bbse_sensor_is_bottleneck":
        lines += [
            "**Oracle固定prior能救回class-specific drift，但BBSE-fixed未全部通过。**",
            "",
            "说明060主要败在prior-drift confounding；下一瓶颈是Judge漂移会污染prior sensor，而不是12维drift表示本身。",
        ]
    else:
        lines += [
            "**连Oracle固定prior也未通过。**",
            "",
            "因此060失败不能只归咎于prior-drift confounding；当前12维Gaussian class-specific drift表示/latent assignment本身仍不足，需要低秩或更强结构约束。",
        ]
    lines += [
        "",
        "## 边界","",
        "- Oracle prior是GT知情诊断，不是部署方法。",
        "- BBSE-fixed才是0标签可部署分支。",
        "- 052/053仍是development内部batch。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    self_test() if args.self_test else main()
