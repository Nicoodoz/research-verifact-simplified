from pathlib import Path
import argparse, csv, hashlib, importlib.util, json, math, subprocess
import numpy as np
from scipy.optimize import minimize

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/062_low_rank_empirical_transport"
O055=ROOT/"outputs/055_zero_label_policy_adaptation"
O061=ROOT/"outputs/061_prior_anchored_drift"
P061=ROOT/"tasks/061_prior_anchored_drift/run061.py"

spec=importlib.util.spec_from_file_location("r061",P061)
r061=importlib.util.module_from_spec(spec)
spec.loader.exec_module(r061)

LABELS=r061.LABELS
FEATURES=["DS_S","DS_NS","Q_S","Q_NS"]
K,D=3,4
RFF_DIM=128
SEED=20260922062
NULL_REPS=10
EVAL_REPS=5
R2_NULL_REPS=5
R2_MIXED_REPS=3
BATCHES=(240,480,960)
PRIORS=r061.PRIORS
DRIFTS=r061.DRIFTS
RANK1_TRUTH={"NS_QNS","NA_DSS","NS_DSNS","S_QS_down"}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

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

def stable_seed(source,suffix):
    h=hashlib.sha256(f"{SEED}:{source}:{suffix}".encode()).hexdigest()
    return int(h[:8],16)

class EmpiricalTransport:
    def __init__(self,source_rows,source_tag):
        self.source_tag=source_tag
        self.U=np.stack([r["u"] for r in source_rows])
        self.y=np.array([r["y"] for r in source_rows],int)
        self.mean=self.U.mean(axis=0)
        self.std=self.U.std(axis=0)
        self.std[self.std<1e-8]=1.0
        self.Z=(self.U-self.mean)/self.std
        self.Zy=[self.Z[self.y==k] for k in range(K)]

        dif=self.Z[:,None,:]-self.Z[None,:,:]
        dist=np.sqrt(np.sum(dif*dif,axis=2))
        nz=dist[np.triu_indices(len(self.Z),1)]
        nz=nz[nz>0]
        self.bandwidth=float(np.median(nz))
        if not np.isfinite(self.bandwidth) or self.bandwidth<=0:
            raise RuntimeError("invalid bandwidth")
        rng=np.random.default_rng(stable_seed(source_tag,"rff"))
        self.W=rng.normal(0.0,1.0/self.bandwidth,size=(D,RFF_DIM))
        self.b=rng.uniform(0.0,2*np.pi,size=RFF_DIM)
        self.scale=math.sqrt(2.0/RFF_DIM)
        self.cmean=[]; self.smean=[]
        for z in self.Zy:
            phase=z@self.W+self.b
            self.cmean.append(np.cos(phase).mean(axis=0))
            self.smean.append(np.sin(phase).mean(axis=0))
        self.cmean=np.stack(self.cmean)
        self.smean=np.stack(self.smean)
        self.mu0=self.scale*self.cmean

    def transform(self,U):
        return (np.asarray(U,float)-self.mean)/self.std

    def _phi(self,Z):
        return self.scale*np.cos(np.asarray(Z,float)@self.W+self.b)

    def target_mean(self,U):
        return self._phi(self.transform(U)).mean(axis=0)

    def class_mean_shifted(self,k,delta):
        t=np.asarray(delta,float)@self.W
        ct=np.cos(t); st=np.sin(t)
        return self.scale*(self.cmean[k]*ct-self.smean[k]*st)

    def class_mean_and_jac(self,k,delta):
        t=np.asarray(delta,float)@self.W
        ct=np.cos(t); st=np.sin(t)
        mu=self.scale*(self.cmean[k]*ct-self.smean[k]*st)
        msin=self.smean[k]*ct+self.cmean[k]*st
        J=(-self.scale*msin)[:,None]*self.W.T
        return mu,J

    def mix_mean(self,prior,delta):
        prior=np.asarray(prior,float)
        mus=np.stack([self.class_mean_shifted(k,delta[k]) for k in range(K)])
        return prior@mus

    def residual(self,target_mu,prior,delta):
        return float(np.linalg.norm(np.asarray(target_mu)-self.mix_mean(prior,delta)))

    def no_shift_residual(self,target_mu,prior):
        return float(np.linalg.norm(np.asarray(target_mu)-np.asarray(prior)@self.mu0))

    @staticmethod
    def rank1_delta(params):
        p=np.asarray(params,float)
        a=p[:K]
        v=p[K:K+D]
        nv=float(np.linalg.norm(v))
        if nv<1e-10:
            v=np.array([1.0,0,0,0])
        else:
            v=v/nv
        return a[:,None]*v[None,:]

    @staticmethod
    def rank2_delta(params):
        p=np.asarray(params,float)
        A=p[:K*2].reshape(K,2)
        V=p[K*2:].reshape(D,2)
        if np.linalg.matrix_rank(V)<2:
            V=V+1e-6*np.array([[1,0],[0,1],[0,0],[0,0]],float)
        Q,_=np.linalg.qr(V)
        return A@Q[:,:2].T

    def fit_rank1(self,U,prior):
        target_mu=self.target_mean(U)
        prior=np.asarray(prior,float)
        def obj_grad(p):
            p=np.asarray(p,float)
            a=p[:K]
            q=p[K:K+D]
            nq=float(np.linalg.norm(q))
            if nq<1e-10:
                v=np.array([1.0,0,0,0])
                nq=1.0
            else:
                v=q/nq
            delta=a[:,None]*v[None,:]
            mus=[]; jacs=[]
            for k in range(K):
                mu,J=self.class_mean_and_jac(k,delta[k])
                mus.append(mu); jacs.append(J)
            mix=prior@np.stack(mus)
            e=mix-target_mu
            obj=float(e@e)
            gdelta=[]
            for k in range(K):
                gdelta.append(2.0*prior[k]*(jacs[k].T@e))
            gdelta=np.stack(gdelta)
            ga=np.array([gdelta[k]@v for k in range(K)])
            gv=np.sum(a[:,None]*gdelta,axis=0)
            P=np.eye(D)-np.outer(v,v)
            gq=(P@gv)/nq
            return obj,np.r_[ga,gq]
        # Deterministic start 1: top rank-1 direction of the full
        # no-shift gradient matrix.
        mus=[]; jacs=[]
        for k in range(K):
            mu,J=self.class_mean_and_jac(k,np.zeros(D))
            mus.append(mu); jacs.append(J)
        e0=prior@np.stack(mus)-target_mu
        G=np.stack([2.0*prior[k]*(jacs[k].T@e0) for k in range(K)])
        _,_,vt=np.linalg.svd(G,full_matrices=False)
        v0=vt[0]
        starts=[np.r_[np.zeros(K),v0]]
        # Deterministic start 2: fixed-seed random direction.
        rng=np.random.default_rng(stable_seed(self.source_tag,"r1_starts"))
        vr=rng.normal(size=D); vr/=np.linalg.norm(vr)
        starts.append(np.r_[np.zeros(K),vr])
        bounds=[(-3,3)]*K+[(-2,2)]*D
        fits=[]
        for s in starts:
            z=minimize(lambda p: obj_grad(p),s,jac=True,method="L-BFGS-B",
                       bounds=bounds,
                       options={"maxiter":80,"ftol":1e-10,"gtol":1e-7})
            fits.append(z)
        best=min(fits,key=lambda z:float(z.fun))
        return {
            "delta_z":self.rank1_delta(best.x),
            "residual":float(math.sqrt(max(float(best.fun),0.0))),
            "success":bool(best.success),
            "nit":int(best.nit),
        }

    def fit_rank2(self,U,prior):
        target_mu=self.target_mean(U)
        def obj(p):
            d=self.rank2_delta(p)
            r=self.residual(target_mu,prior,d)
            return r*r
        starts=[]
        pairs=[(0,1),(0,2),(2,3)]
        for i,j in pairs:
            V=np.zeros((D,2)); V[i,0]=1.0; V[j,1]=1.0
            starts.append(np.r_[np.zeros(K*2),V.ravel()])
        rng=np.random.default_rng(stable_seed(self.source_tag,"r2_starts"))
        V=rng.normal(size=(D,2))
        starts.append(np.r_[np.zeros(K*2),V.ravel()])
        bounds=[(-3,3)]*(K*2)+[(-2,2)]*(D*2)
        fits=[]
        for s in starts:
            z=minimize(obj,s,method="L-BFGS-B",bounds=bounds,
                       options={"maxiter":100,"ftol":1e-10,"gtol":1e-7})
            fits.append(z)
        best=min(fits,key=lambda z:float(z.fun))
        return {
            "delta_z":self.rank2_delta(best.x),
            "residual":float(math.sqrt(max(float(best.fun),0.0))),
            "success":bool(best.success),
            "nit":int(best.nit),
        }

    def cv_gain(self,U,prior,rank=1):
        U=np.asarray(U,float)
        ia=np.arange(len(U))%2==0
        ib=~ia
        gains=[]; deltas=[]
        for fitmask,evalmask in ((ia,ib),(ib,ia)):
            fit=(self.fit_rank1(U[fitmask],prior) if rank==1
                 else self.fit_rank2(U[fitmask],prior))
            mu=self.target_mean(U[evalmask])
            r0=self.no_shift_residual(mu,prior)
            r1=self.residual(mu,prior,fit["delta_z"])
            gains.append(r0-r1)
            deltas.append(fit["delta_z"])
        return {
            "gain":float(np.mean(gains)),
            "fold_gain_1":float(gains[0]),
            "fold_gain_2":float(gains[1]),
            "fold_delta_mean":np.mean(np.stack(deltas),axis=0),
        }

def null_threshold(model,source_rows,prior,n,rank,reps,rng):
    gains=[]
    zero=np.zeros((K,D),float)
    for _ in range(reps):
        U,_,_=r061.sample_target(source_rows,prior,n,zero,rng)
        gains.append(model.cv_gain(U,prior,rank=rank)["gain"])
    gains=np.asarray(gains,float)
    return {
        "threshold95":float(np.quantile(gains,.95)),
        "gain_mean":float(gains.mean()),
        "gain_std":float(gains.std()),
        "gains":gains,
    }

def delta_raw(model,delta_z):
    return np.asarray(delta_z,float)*model.std[None,:]

def delta_metrics(est,true,weights=None,sign_cut=1e-12):
    est=np.asarray(est,float); true=np.asarray(true,float)
    err=est-true
    mae=float(np.mean(np.abs(err)))
    mask=np.abs(true)>=sign_cut
    sign=np.nan
    if np.any(mask):
        sign=float(np.mean(np.sign(est[mask])==np.sign(true[mask])))
    if weights is None:
        weights=np.full(K,1.0/K)
    weights=np.asarray(weights,float)
    total=float(np.sum(weights[:,None]*(true*true)))
    resid=float(np.sum(weights[:,None]*(err*err)))
    r2=np.nan if total<1e-12 else 1-resid/total
    return {"mae":mae,"sign":sign,"r2":float(r2),"resid":resid,"total":total}

def flatten_delta(prefix,delta):
    out={}
    for y in range(K):
        yn=LABELS[y].replace(" ","_")
        for j,f in enumerate(FEATURES):
            out[f"{prefix}_{yn}_{f}"]=float(delta[y,j])
    return out

def actual_true_delta(source_rows,target_rows):
    Us=np.stack([r["u"] for r in source_rows])
    ys=np.array([r["y"] for r in source_rows],int)
    Ut=np.stack([r["u"] for r in target_rows])
    yt=np.array([r["y"] for r in target_rows],int)
    mus=np.stack([Us[ys==k].mean(axis=0) for k in range(K)])
    mut=np.stack([Ut[yt==k].mean(axis=0) for k in range(K)])
    return mut-mus

def svd_energy(delta):
    s=np.linalg.svd(np.asarray(delta,float),compute_uv=False)
    e=s*s
    total=float(e.sum())
    if total<=0:
        return 0.0,0.0,s
    return float(e[0]/total),float(e[:2].sum()/total),s

def active_metrics(est,true):
    est=np.asarray(est,float); true=np.asarray(true,float)
    active=np.abs(true)>1e-12
    inactive=~active
    active_mae=np.nan
    sign=np.nan
    if np.any(active):
        active_mae=float(np.mean(np.abs(est[active]-true[active])))
        sign=float(np.mean(np.sign(est[active])==np.sign(true[active])))
    inactive_mae=float(np.mean(np.abs(est[inactive]))) if np.any(inactive) else 0.0
    return active_mae,inactive_mae,sign

def freeze():
    inputs={
        "features_qwen_052":O055/"features_qwen_052.jsonl",
        "features_qwen_053":O055/"features_qwen_053.jsonl",
        "run061":P061,
        "actual061":O061/"actual_evaluation.csv",
        "protocol":ROOT/"tasks/062_low_rank_empirical_transport/protocol.md",
    }
    obj={
        "git_head":subprocess.check_output(
            ["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"rff_dim":RFF_DIM,
        "null_reps":NULL_REPS,"eval_reps":EVAL_REPS,
        "rank2_null_reps":R2_NULL_REPS,"rank2_mixed_reps":R2_MIXED_REPS,
        "batches":list(BATCHES),
        "priors":{k:v.tolist() for k,v in PRIORS.items()},
        "drifts":{k:v.tolist() for k,v in DRIFTS.items()},
        "rank1_truth_patterns":sorted(RANK1_TRUTH),
        "code_sha256":sha(Path(__file__)),
        "inputs":{
            k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)}
            for k,v in inputs.items()
        },
    }
    put(OUT/"freeze.json",obj)
    return obj

def self_test():
    pools={k:r061.load_pool(k,True) for k in ("052","053")}
    model=EmpiricalTransport(pools["052"],"052")
    rng=np.random.default_rng(123)
    prior=np.array([.6,.25,.15])
    U,_,rel=r061.sample_target(
        pools["052"],prior,240,DRIFTS["NS_QNS"],rng)
    pb=r061.bbse_prior(pools["052"],rel)
    cv=model.cv_gain(U,pb,rank=1)
    fit=model.fit_rank1(U,pb)
    est=delta_raw(model,fit["delta_z"])
    am,im,sg=active_metrics(est,DRIFTS["NS_QNS"])
    U0,_,_=r061.sample_target(
        pools["052"],prior,240,np.zeros((K,D)),rng)
    cv0=model.cv_gain(U0,prior,rank=1)
    if not np.all(np.isfinite(est)) or not np.isfinite(cv["gain"]):
        raise AssertionError("nonfinite rank1")
    print("062 SELF-TEST PASS",{
        "bandwidth":model.bandwidth,
        "drift_gain":cv["gain"],
        "null_gain":cv0["gain"],
        "active_mae":am,"inactive_mae":im,"sign":sg,
        "bbse_l1":float(np.sum(np.abs(pb-prior))),
    })

def fit_accept(model,U,prior,rank,threshold):
    cv=model.cv_gain(U,prior,rank=rank)
    accept=bool(cv["gain"]>threshold)
    if accept:
        fit=model.fit_rank1(U,prior) if rank==1 else model.fit_rank2(U,prior)
        dz=fit["delta_z"]
        residual=fit["residual"]
    else:
        dz=np.zeros((K,D),float)
        residual=model.no_shift_residual(model.target_mean(U),prior)
    return {
        "gain":cv["gain"],
        "fold_gain_1":cv["fold_gain_1"],
        "fold_gain_2":cv["fold_gain_2"],
        "accept":accept,
        "delta_z":dz,
        "delta_raw":delta_raw(model,dz),
        "residual":float(residual),
    }

def synthetic_rank1_condition(model,source_rows,prior,n,drift,threshold,rng):
    vals=[]
    for _ in range(EVAL_REPS):
        U,_,rel=r061.sample_target(source_rows,prior,n,drift,rng)
        pb=r061.bbse_prior(source_rows,rel)
        z=fit_accept(model,U,pb,1,threshold)
        am,im,sg=active_metrics(z["delta_raw"],drift)
        dm=delta_metrics(z["delta_raw"],drift,prior)
        vals.append({
            "accept":float(z["accept"]),
            "gain":z["gain"],
            "bbse_l1":float(np.sum(np.abs(pb-prior))),
            "active_mae":am,
            "inactive_mae":im,
            "sign":sg,
            "full_mae":dm["mae"],
            "full_r2":dm["r2"],
        })
    def m(key,finite=False):
        x=np.array([v[key] for v in vals],float)
        if finite:
            x=x[np.isfinite(x)]
        return float(np.mean(x)) if len(x) else np.nan
    return {
        "accept_rate":m("accept"),
        "heldout_gain_mean":m("gain"),
        "bbse_l1_mean":m("bbse_l1"),
        "active_mae_mean":m("active_mae",True),
        "inactive_mae_mean":m("inactive_mae"),
        "sign_accuracy":m("sign",True),
        "full_mae_mean":m("full_mae"),
        "full_r2_mean":m("full_r2",True),
    }

def synthetic_rank2_mixed(model,source_rows,prior,threshold,rng):
    vals=[]
    drift=DRIFTS["mixed"]
    n=960
    for _ in range(R2_MIXED_REPS):
        U,_,rel=r061.sample_target(source_rows,prior,n,drift,rng)
        pb=r061.bbse_prior(source_rows,rel)
        z=fit_accept(model,U,pb,2,threshold)
        dm=delta_metrics(z["delta_raw"],drift,prior)
        vals.append({
            "accept":float(z["accept"]),
            "gain":z["gain"],
            "bbse_l1":float(np.sum(np.abs(pb-prior))),
            "mae":dm["mae"],"r2":dm["r2"],
        })
    return {
        "accept_rate":float(np.mean([v["accept"] for v in vals])),
        "heldout_gain_mean":float(np.mean([v["gain"] for v in vals])),
        "bbse_l1_mean":float(np.mean([v["bbse_l1"] for v in vals])),
        "delta_mae_mean":float(np.mean([v["mae"] for v in vals])),
        "delta_r2_mean":float(np.mean([v["r2"] for v in vals])),
    }

def actual_blind_one(source,target,source_rows):
    model=EmpiricalTransport(source_rows,source)
    tb=r061.load_pool(target,False)
    U=np.stack([r["u"] for r in tb])
    rel=np.stack([r["ds_rel"] for r in tb])
    pb=r061.bbse_prior(source_rows,rel)
    out=[]
    for rank,reps in ((1,NULL_REPS),(2,R2_NULL_REPS)):
        rng=np.random.default_rng(stable_seed(source,f"actual_null:{target}:r{rank}"))
        null=null_threshold(model,source_rows,pb,len(U),rank,reps,rng)
        z=fit_accept(model,U,pb,rank,null["threshold95"])
        row={
            "source":source,"target":target,"rank":rank,"target_n":len(U),
            "pi_S":pb[0],"pi_NS":pb[1],"pi_NA":pb[2],
            "null_threshold95":null["threshold95"],
            "null_gain_mean":null["gain_mean"],
            "heldout_gain":z["gain"],
            "fold_gain_1":z["fold_gain_1"],
            "fold_gain_2":z["fold_gain_2"],
            "accept":bool(z["accept"]),
            "full_residual":z["residual"],
            "bandwidth":model.bandwidth,
            **flatten_delta("delta_hat",z["delta_raw"]),
        }
        out.append((row,z["delta_raw"]))
    return out

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    for name in ("freeze.json","actual_unlabeled.csv","synthetic_summary.csv"):
        if (OUT/name).exists():
            raise RuntimeError("formal output exists: "+name)
    fr=freeze()
    pools={k:r061.load_pool(k,True) for k in ("052","053")}
    models={k:EmpiricalTransport(pools[k],k) for k in ("052","053")}

    # Actual target: GT-blind results are frozen first.
    actual_rows=[]
    actual_delta={}
    for source,target in (("052","053"),("053","052")):
        for row,delta in actual_blind_one(source,target,pools[source]):
            actual_rows.append(row)
            actual_delta[(source,target,int(row["rank"]))]=delta
    csvwrite(OUT/"actual_unlabeled.csv",actual_rows)
    blind_sha=sha(OUT/"actual_unlabeled.csv")

    # Source-only null calibration for formal synthetic rank-1 screen.
    null_rows=[]
    thresholds={}
    for source in ("052","053"):
        model=models[source]
        for prior_name,prior in PRIORS.items():
            for n in BATCHES:
                rng=np.random.default_rng(
                    stable_seed(source,f"null:r1:{prior_name}:{n}"))
                z=null_threshold(
                    model,pools[source],prior,n,1,NULL_REPS,rng)
                thresholds[(source,prior_name,n,1)]=z["threshold95"]
                null_rows.append({
                    "source":source,"prior":prior_name,"batch_n":n,"rank":1,
                    "reps":NULL_REPS,"threshold95":z["threshold95"],
                    "gain_mean":z["gain_mean"],"gain_std":z["gain_std"],
                })
                print("062 null r1",source,prior_name,n,flush=True)

    synthetic=[]
    for source in ("052","053"):
        model=models[source]
        for prior_name,prior in PRIORS.items():
            for n in BATCHES:
                threshold=thresholds[(source,prior_name,n,1)]
                for drift_name,drift in DRIFTS.items():
                    rng=np.random.default_rng(
                        stable_seed(source,f"eval:r1:{prior_name}:{n}:{drift_name}"))
                    z=synthetic_rank1_condition(
                        model,pools[source],prior,n,drift,threshold,rng)
                    synthetic.append({
                        "source":source,"prior":prior_name,"batch_n":n,
                        "rank":1,"drift":drift_name,
                        "threshold95":threshold,**z,
                    })
                    print("062 eval r1",source,prior_name,n,drift_name,flush=True)

    # Rank-2 diagnostic only for n=960 mixed.
    for source in ("052","053"):
        model=models[source]
        for prior_name,prior in PRIORS.items():
            rng=np.random.default_rng(
                stable_seed(source,f"null:r2:{prior_name}:960"))
            znull=null_threshold(
                model,pools[source],prior,960,2,R2_NULL_REPS,rng)
            thresholds[(source,prior_name,960,2)]=znull["threshold95"]
            null_rows.append({
                "source":source,"prior":prior_name,"batch_n":960,"rank":2,
                "reps":R2_NULL_REPS,"threshold95":znull["threshold95"],
                "gain_mean":znull["gain_mean"],"gain_std":znull["gain_std"],
            })
            rng=np.random.default_rng(
                stable_seed(source,f"eval:r2:{prior_name}:960:mixed"))
            z=synthetic_rank2_mixed(
                model,pools[source],prior,znull["threshold95"],rng)
            synthetic.append({
                "source":source,"prior":prior_name,"batch_n":960,
                "rank":2,"drift":"mixed",
                "threshold95":znull["threshold95"],**z,
            })
            print("062 diag r2",source,prior_name,flush=True)

    csvwrite(OUT/"null_summary.csv",null_rows)
    csvwrite(OUT/"synthetic_summary.csv",synthetic)

    # GT unblind only after actual_unlabeled.csv is frozen.
    old061={
        (r["source"],r["target"],r["mode"]):r
        for r in read_csv(O061/"actual_evaluation.csv")
    }
    eval_rows=[]
    for source,target in (("052","053"),("053","052")):
        te=r061.load_pool(target,True)
        yt=np.array([r["y"] for r in te],int)
        true_pi=np.bincount(yt,minlength=K)/len(yt)
        true_delta=actual_true_delta(pools[source],te)
        e1,e2,sv=svd_energy(true_delta)
        for rank in (1,2):
            row=next(r for r in actual_rows
                     if r["source"]==source and r["target"]==target
                     and int(r["rank"])==rank)
            est=actual_delta[(source,target,rank)]
            dm=delta_metrics(est,true_delta,true_pi,sign_cut=.5)
            eval_rows.append({
                "source":source,"target":target,"rank":rank,
                "accept":bool(row["accept"]),
                "heldout_gain":float(row["heldout_gain"]),
                "null_threshold95":float(row["null_threshold95"]),
                "true_S":true_pi[0],"true_NS":true_pi[1],"true_NA":true_pi[2],
                "bbse_prior_L1":float(
                    abs(float(row["pi_S"])-true_pi[0])+
                    abs(float(row["pi_NS"])-true_pi[1])+
                    abs(float(row["pi_NA"])-true_pi[2])),
                "delta_MAE":dm["mae"],
                "weighted_R2":dm["r2"],
                "meaningful_sign_accuracy":dm["sign"],
                "true_rank1_energy":e1,
                "true_rank2_energy":e2,
                "sv1":float(sv[0]),
                "sv2":float(sv[1]) if len(sv)>1 else 0.0,
                "sv3":float(sv[2]) if len(sv)>2 else 0.0,
                "gaussian061_R2":float(
                    old061[(source,target,"bbse")]["class_specific_R2"]),
                **flatten_delta("delta_true",true_delta),
            })
    csvwrite(OUT/"actual_evaluation.csv",eval_rows)

    r1_960=[r for r in synthetic
            if int(r["rank"])==1 and int(r["batch_n"])==960]
    none_rows=[r for r in r1_960 if r["drift"]=="none"]
    truth_rows=[r for r in r1_960 if r["drift"] in RANK1_TRUTH]
    false_accept=float(np.mean([r["accept_rate"] for r in none_rows]))
    detection=float(np.mean([r["accept_rate"] for r in truth_rows]))
    active_mae=float(np.mean([
        r["active_mae_mean"] for r in truth_rows
        if np.isfinite(r["active_mae_mean"])]))
    sign_acc=float(np.mean([
        r["sign_accuracy"] for r in truth_rows
        if np.isfinite(r["sign_accuracy"])]))
    inactive_mae=float(np.mean([r["inactive_mae_mean"] for r in truth_rows]))
    synthetic_pass=bool(
        false_accept<=.10 and detection>=.80 and
        active_mae<=.30 and sign_acc>=.90)

    a1=[r for r in eval_rows if int(r["rank"])==1]
    a2=[r for r in eval_rows if int(r["rank"])==2]
    actual_rank1_pass=bool(all(
        bool(r["accept"]) and float(r["weighted_R2"])>=.50 for r in a1))
    rank2_worth_formalizing=bool(all(
        bool(r["accept"]) and float(r["weighted_R2"])>=.50 for r in a2))

    r2mixed=[r for r in synthetic if int(r["rank"])==2]
    r2diag={
        "mixed_accept_rate_mean":float(np.mean([r["accept_rate"] for r in r2mixed])),
        "mixed_delta_mae_mean":float(np.mean([r["delta_mae_mean"] for r in r2mixed])),
        "mixed_delta_r2_mean":float(np.mean([r["delta_r2_mean"] for r in r2mixed])),
    }
    screen={
        "rank1_n960_none_false_accept":false_accept,
        "rank1_n960_truth_accept":detection,
        "rank1_n960_active_mae":active_mae,
        "rank1_n960_inactive_spurious_mae":inactive_mae,
        "rank1_n960_sign_accuracy":sign_acc,
        "synthetic_rank1_pass":synthetic_pass,
    }
    if synthetic_pass and actual_rank1_pass:
        diagnosis="rank1_empirical_transport_passes_for_dynamic_decision"
    elif rank2_worth_formalizing:
        diagnosis="rank1_insufficient_rank2_worth_formalizing"
    elif not synthetic_pass:
        diagnosis="rank1_empirical_transport_fails_synthetic_screen"
    else:
        diagnosis="rank1_synthetic_pass_but_actual_transfer_not_recovered"

    run={
        "status":"PASS","git_head":fr["git_head"],
        "new_api_calls":0,"reserved_used":False,
        "actual_unlabeled_sha256_before_gt_evaluation":blind_sha,
        "pools":{k:len(v) for k,v in pools.items()},
        "synthetic_screen":screen,
        "rank2_diagnostic":r2diag,
        "actual_rank1_pass":actual_rank1_pass,
        "rank2_worth_formalizing":rank2_worth_formalizing,
        "diagnosis":diagnosis,
        "advance_to_dynamic_decision":bool(synthetic_pass and actual_rank1_pass),
    }
    put(OUT/"run_summary.json",run)
    write_report(actual_rows,eval_rows,run)
    print("062 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(actual_rows,eval_rows,run):
    s=run["synthetic_screen"]
    r2=run["rank2_diagnostic"]
    lines=[
        "# 062：Low-rank Empirical Transport for Zero-label Judge Drift","",
        "## 方法","",
        "BBSE只负责target类别比例；Judge drift不再用Gaussian latent mixture，而是直接平移source三类经验score分布并用RFF/MMD匹配target无标签分布。主模型为rank-1：delta_y=a_y v；rank-2仅作诊断。","",
        "所有actual GT-blind结果先写入actual_unlabeled.csv并冻结SHA256，之后才解盲评价。","",
        "## Synthetic rank-1 screen（n=960）","",
        f'- none false-accept: **{s["rank1_n960_none_false_accept"]:.1%}**',
        f'- rank-1真值pattern accept: **{s["rank1_n960_truth_accept"]:.1%}**',
        f'- active-coordinate delta MAE: **{s["rank1_n960_active_mae"]:.3f}**',
        f'- inactive spurious MAE: **{s["rank1_n960_inactive_spurious_mae"]:.3f}**',
        f'- sign accuracy: **{s["rank1_n960_sign_accuracy"]:.1%}**',
        f'- 事前synthetic门槛：**{"PASS" if s["synthetic_rank1_pass"] else "FAIL"}**',
        "",
        "## 真实052↔053","",
        "| direction | rank | accept | gain / q95 | BBSE L1 | R2 | MAE | sign | true rank1/rank2 energy | 061 Gaussian R2 |",
        "|---|---:|---|---|---:|---:|---:|---:|---|---:|",
    ]
    for r in eval_rows:
        lines.append(
            f'| {r["source"]}→{r["target"]} | {r["rank"]} | {r["accept"]} | '
            f'{r["heldout_gain"]:.4f} / {r["null_threshold95"]:.4f} | '
            f'{r["bbse_prior_L1"]:.3f} | {r["weighted_R2"]:.3f} | '
            f'{r["delta_MAE"]:.3f} | {r["meaningful_sign_accuracy"]:.3f} | '
            f'{r["true_rank1_energy"]:.3f}/{r["true_rank2_energy"]:.3f} | '
            f'{r["gaussian061_R2"]:.3f} |')
    lines += [
        "",
        "## Rank-2 mixed diagnostic","",
        f'- mixed accept mean: **{r2["mixed_accept_rate_mean"]:.1%}**',
        f'- mixed delta MAE mean: **{r2["mixed_delta_mae_mean"]:.3f}**',
        f'- mixed delta R2 mean: **{r2["mixed_delta_r2_mean"]:.3f}**',
        "",
        "## 结论","",
    ]
    diag=run["diagnosis"]
    if diag=="rank1_empirical_transport_passes_for_dynamic_decision":
        lines += [
            "**rank-1 empirical transport同时通过synthetic和真实两方向门槛。**",
            "",
            "可以进入下一步dynamic decision研究，但仍需在新数据/患者级独立样本上验证。",
        ]
    elif diag=="rank1_insufficient_rank2_worth_formalizing":
        lines += [
            "**rank-1不足，但rank-2在真实两方向达到事前诊断门槛。**",
            "",
            "下一步应正式化rank-2并重新做source-null/synthetic门槛，而不是直接进入动态分类。",
        ]
    elif diag=="rank1_empirical_transport_fails_synthetic_screen":
        lines += [
            "**rank-1 empirical transport连source-controlled synthetic门槛都未通过。**",
            "",
            "说明低秩经验平移本身仍不能稳定解决伪漂移/恢复问题，不应仅凭真实development fit继续堆同类参数。",
        ]
    else:
        lines += [
            "**rank-1通过synthetic，但真实052↔053没有同时恢复到R2>=0.50。**",
            "",
            "说明经验transport解决了一部分061问题，但当前低秩平移仍不足以解释真实Judge behavior shift。",
        ]
    lines += [
        "",
        "## 边界","",
        "- low-rank结构来自development GT诊断启发，真实052/053结果不是独立外部验证。",
        "- rank-2仅为诊断上限。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--self-test",action="store_true")
    args=ap.parse_args()
    self_test() if args.self_test else main()
