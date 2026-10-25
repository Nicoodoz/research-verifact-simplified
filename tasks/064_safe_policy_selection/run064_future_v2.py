from pathlib import Path
import hashlib, importlib.util, json, subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/064_safe_policy_selection"
P064=ROOT/"tasks/064_safe_policy_selection/run064.py"

spec=importlib.util.spec_from_file_location("r064",P064)
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

BUDGETS=r.BUDGETS
REPS=50
SEED=202609230642

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,obj):
    Path(p).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def split_rng(source,target,rep):
    h=hashlib.sha256(f"{SEED}:{source}:{target}:{rep}:split".encode()).hexdigest()
    return np.random.default_rng(int(h[:16],16))

def split_patients(rows,source,target,rep):
    sids=sorted(set(x["sid"] for x in rows))
    rng=split_rng(source,target,rep)
    sids=np.array(sids,object);rng.shuffle(sids)
    cut=max(1,len(sids)//2)
    cal=set(sids[:cut].tolist())
    future=set(sids[cut:].tolist())
    a=[x for x in rows if x["sid"] in cal]
    b=[x for x in rows if x["sid"] in future]
    assert a and b and not (cal&future)
    return a,b,len(cal),len(future)

def one_future(source,target,source_rows,target_rows,strategy,budget,rep,
               shapes,oracle_name,safe_set):
    cal,future,ncal,nfuture=split_patients(target_rows,source,target,rep)
    arng=r.seeded_rng(source,target,strategy,budget,rep,"future_acquire")
    if budget==0:
        idx=[]
    elif strategy=="random_global":
        idx=r.random_global_indices(cal,budget,arng)
    elif strategy=="active_policy":
        idx=r.active_select_indices(cal,budget,shapes,arng)
    else:
        raise ValueError(strategy)

    lc=r.label_counts_from(cal,idx)
    tc=r.target_sig_counts(cal)
    # Future deployment: labeled calibration examples estimate reliability,
    # but policy exposure is the full calibration unlabeled signature mix.
    rem=tc.copy()
    mrng=r.seeded_rng(source,target,strategy,budget,rep,"future_mc")
    selected,post=r.select_policy(shapes,lc,tc,rem,mrng)

    pp=r.policy_predict(future,selected)
    bp=r.policy_predict(future,"BASE")
    pm=r.r063.metrics(future,pp);bm=r.r063.metrics(future,bp)
    ylab=np.array([cal[i]["y"] for i in idx],int) if idx else np.array([],int)
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
        "labeled_disagreement":int(sum(len(set(cal[i]["signature"]))>1 for i in idx)),
        "actual_labels_used":len(idx),"calibration_patients":ncal,"future_patients":nfuture,
        "future_n":len(future),
        "post_mean_gain":chosen["mean_gain"],"post_p_gain":chosen["p_gain"],
        "post_rescue_risk":chosen["rescue_risk"],"post_veto_harm":chosen["veto_harm"],
    }
    for pref,m in (("policy",pm),("base",bm)):
        for k,v in m.items(): row[f"{pref}_{k}"]=v
    for k in ("PA","MCC","falseS_rate","S","NS","NA"):
        row[f"delta_{k}"]=pm[k]-bm[k]
    return row

def freeze():
    inputs={
        "run064":P064,
        "amendment":ROOT/"tasks/064_safe_policy_selection/protocol_amendment_002.md",
        "features_qwen_052":ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl",
        "features_qwen_053":ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_053.jsonl",
    }
    obj={
        "git_head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "seed":SEED,"budgets":list(BUDGETS),"reps":REPS,
        "code_sha256":sha(Path(__file__)),
        "inputs":{k:{"path":str(v.relative_to(ROOT)),"sha256":sha(v)} for k,v in inputs.items()},
    }
    put(OUT/"future_v2_freeze.json",obj);return obj

def self_test():
    rows=r.load_pool("053",True)
    cal,fut,nc,nf=split_patients(rows,"052","053",0)
    assert set(x["sid"] for x in cal).isdisjoint(set(x["sid"] for x in fut))
    shapes=r.source_shapes(r.load_pool("052",True))
    oname,safe,_=r.oracle_info(rows)
    z=one_future("052","053",r.load_pool("052",True),rows,"active_policy",3,0,shapes,oname,safe)
    assert z["actual_labels_used"]<=3 and z["future_n"]==len(fut)
    print("064 FUTURE V2 SELF-TEST PASS",{"cal_patients":nc,"future_patients":nf,"selected":z["selected_policy"],"labels":z["actual_labels_used"]})

def main():
    for n in ("future_v2_freeze.json","future_v2_replicate_results.csv","future_v2_summary.csv"):
        if (OUT/n).exists(): raise RuntimeError("formal output exists: "+n)
    fr=freeze()
    pools={k:r.load_pool(k,True) for k in ("052","053")}
    oracle_cache={}
    for source,target in (("052","053"),("053","052")):
        oracle_cache[(source,target)]=r.oracle_info(pools[target])

    rows=[]
    for source,target in (("052","053"),("053","052")):
        src=pools[source];tgt=pools[target];shapes=r.source_shapes(src)
        oname,safe,_=oracle_cache[(source,target)]
        for rep in range(REPS):
            rows.append(one_future(source,target,src,tgt,"zero_label",0,rep,shapes,oname,safe))
        print("064 future",source,"->",target,"zero",flush=True)
        for strategy in ("random_global","active_policy"):
            for budget in BUDGETS[1:]:
                for rep in range(REPS):
                    rows.append(one_future(source,target,src,tgt,strategy,budget,rep,shapes,oname,safe))
                print("064 future",source,"->",target,strategy,budget,flush=True)

    r.csvwrite(OUT/"future_v2_replicate_results.csv",rows)
    summary=r.summarize(rows)
    for z in summary:
        x=[q for q in rows if (q["source"],q["target"],q["strategy"],q["budget"])==(z["source"],z["target"],z["strategy"],z["budget"])]
        z["mean_actual_labels_used"]=float(np.mean([q["actual_labels_used"] for q in x]))
        z["mean_future_n"]=float(np.mean([q["future_n"] for q in x]))
        z["direction_pass"]=r.direction_pass(z)
    r.csvwrite(OUT/"future_v2_summary.csv",summary)
    min_budget=r.minimum_active_budget(summary)
    run={
        "status":"PASS","git_head":fr["git_head"],"new_api_calls":0,"reserved_used":False,
        "pools":{k:len(v) for k,v in pools.items()},
        "oracle_policy":{f"{s}->{t}":oracle_cache[(s,t)][0] for s,t in (("052","053"),("053","052"))},
        "minimum_active_budget":min_budget,
        "missing_link_closed":bool(min_budget is not None),
    }
    put(OUT/"future_v2_run_summary.json",run)
    write_report(summary,run)
    print("064 FUTURE V2 COMPLETE",json.dumps(run,ensure_ascii=False))

def write_report(summary,run):
    lines=[
        "# 064 Amendment 002：Future-policy Exposure Fix","",
        "少量标签只来自calibration patients；选定policy后，应用到sid完全不重叠的future patients。policy库、posterior、风险阈值均与主064相同。","",
        "| direction | strategy | budget | oracle match | unsafe | BASE fallback | ΔPA | ΔMCC | ΔNS | ΔNA | labels used | pass |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for z in summary:
        if z["budget"]==0: continue
        lines.append(
            f'| {z["source"]}→{z["target"]} | {z["strategy"]} | {z["budget"]} | '
            f'{z["oracle_match_rate"]:.1%} | {z["unsafe_switch_rate"]:.1%} | '
            f'{z["base_fallback_rate"]:.1%} | {z["mean_delta_PA"]:+.3f} | '
            f'{z["mean_delta_MCC"]:+.3f} | {z["mean_delta_NS"]:+.3f} | '
            f'{z["mean_delta_NA"]:+.3f} | {z["mean_actual_labels_used"]:.1f} | '
            f'{z["direction_pass"]} |')
    lines += ["","## 结论",""]
    if run["missing_link_closed"]:
        lines += [
            f'**patient-disjoint评估下，active_policy在budget={run["minimum_active_budget"]}时闭合少标签policy认证链路。**',
            "",
            "说明少量target标签可以用于当前环境的局部policy认证，并泛化到未见患者；下一步应固定该budget做更独立数据验证。",
        ]
    else:
        lines += [
            "**patient-disjoint评估下，0/3/5/10/20 labels仍未在两个方向同时通过。**",
            "",
            "这时失败不能再归因于within-batch action region被标注耗尽，需要看是认证样本不足还是source先验/active acquisition仍不合适。",
        ]
    lines += [
        "",
        "## 边界","",
        "- calibration/future按sid完全分离，但仍来自同一development target pool。",
        "- oracle policy沿用完整target GT，仅作诊断。",
        "- 0 API、未使用reserved、未自动commit/push。",
    ]
    (OUT/"future_v2_report.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":
    import sys
    if "--self-test" in sys.argv: self_test()
    else: main()
