from pathlib import Path
from collections import Counter,defaultdict
import csv,json,sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/067_conservative_evidence_packing"))
import common067 as c
import run067

LAB=list(c.LABELS);LI={x:i for i,x in enumerate(LAB)}
def mcc(y,p):
    M=np.zeros((3,3),float);np.add.at(M,(y,p),1)
    s=M.sum();cc=np.trace(M);a=M.sum(1);b=M.sum(0)
    den=((s*s-a@a)*(s*s-b@b))**.5
    return float((cc*s-a@b)/den) if den else 0.0
def metrics(rows,pkey):
    y=np.array([LI[r["GT"]] for r in rows]);p=np.array([LI[r[pkey]] for r in rows])
    M=np.zeros((3,3),int);np.add.at(M,(y,p),1)
    rec=[M[k,k]/M[k].sum() if M[k].sum() else float("nan") for k in range(3)]
    fs=int(((y!=0)&(p==0)).sum());nons=int((y!=0).sum())
    return dict(n=len(rows),correct=int((y==p).sum()),PA=float((y==p).mean()),MCC=mcc(y,p),
                falseS=fs,falseS_rate=fs/nons,S=float(rec[0]),NS=float(rec[1]),NA=float(rec[2]),
                confusion=M.tolist())
def bootstrap(rows,B=1000,seed=20260923067):
    by=defaultdict(list)
    for r in rows:by[r["sid"]].append(r)
    sids=sorted(by);rng=np.random.default_rng(seed);out=[]
    for _ in range(B):
        draw=rng.choice(sids,size=len(sids),replace=True)
        sample=[]
        for j,sid in enumerate(draw):
            # duplicate patient clusters are allowed; metrics do not use sid.
            sample.extend(by[str(sid)])
        a=metrics(sample,"baseline_pg");b=metrics(sample,"new_pg")
        out.append((b["PA"]-a["PA"],b["MCC"]-a["MCC"],b["falseS"]-a["falseS"]))
    A=np.asarray(out,float)
    return {
      "B":B,
      "delta_PA_mean":float(A[:,0].mean()),"delta_PA_ci":[float(x) for x in np.quantile(A[:,0],[.025,.975])],
      "delta_MCC_mean":float(A[:,1].mean()),"delta_MCC_ci":[float(x) for x in np.quantile(A[:,1],[.025,.975])],
      "delta_falseS_mean":float(A[:,2].mean()),"delta_falseS_ci":[float(x) for x in np.quantile(A[:,2],[.025,.975])],
    }
def main():
    feats={x["id"]:x for x in c.lines(ROOT/"outputs/055_zero_label_policy_adaptation/features_qwen_052.jsonl")}
    preds={r["id"]:r for r in csv.DictReader(open(ROOT/"outputs/052_first_tier_validation/predictions.csv",encoding="utf-8-sig"))}
    cases={x["id"]:x for x in c.lines(c.OUT/"cases_blind.jsonl")}
    packs={x["id"]:x for x in c.lines(c.OUT/"pack_mapping.jsonl")}
    attempts,term=run067.state()
    formal_ids={x["request_id"] for fn in ("stage1_jobs.jsonl","stage2_jobs.jsonl") for x in c.lines(c.OUT/fn)}
    formal_attempts=[a for a in attempts if a["request_id"] in formal_ids]
    superseded_attempts=[a for a in attempts if a["request_id"] not in formal_ids]
    rows=[]
    for pid,x in cases.items():
        f=feats[pid];pr=preds[pid];mp=packs[pid]
        b_scores=f["ts_scores"];baseline_pg=c.priorg(b_scores)
        baseline_raw=pr["TS_raw"]
        new_scores=b_scores;new_raw=baseline_raw;judge_valid=False
        rid=mp.get("judge_request_id")
        if mp.get("changed") and rid and rid in term:
            z=term[rid]["parsed"]
            judge_valid=z.get("status") in ("valid","valid_with_format_anomaly") and z.get("scores") and z.get("verdict") in LAB
            if judge_valid:
                new_scores=z["scores"];new_raw=z["verdict"]
        new_pg=c.priorg(new_scores)
        rows.append(dict(id=pid,sid=str(f["sid"]),author=f["author"],GT=f["GT"],
                         mapped=x["mapped"],changed=mp.get("changed",False),judge_valid=bool(judge_valid),
                         fallback=mp.get("fallback"),baseline_raw=baseline_raw,new_raw=new_raw,
                         baseline_pg=baseline_pg,new_pg=new_pg,
                         added_n=len(mp.get("added_pids",[])),dropped_n=len(mp.get("dropped_pids",[])),
                         addition_roles=";".join(mp.get("addition_roles",[])),
                         baseline_body_chars=mp.get("baseline_body_chars"),
                         final_body_chars=mp.get("final_body_chars")))
    c.require(len(rows)==236,"row count")
    base=metrics(rows,"baseline_pg");new=metrics(rows,"new_pg")
    raw0=metrics(rows,"baseline_raw");raw1=metrics(rows,"new_raw")
    rescue=[r for r in rows if r["baseline_pg"]!=r["GT"] and r["new_pg"]==r["GT"]]
    harm=[r for r in rows if r["baseline_pg"]==r["GT"] and r["new_pg"]!=r["GT"]]
    changed=[r for r in rows if r["changed"]]
    invalid=[r for r in changed if not r["judge_valid"]]
    patient_delta={}
    for sid in sorted({r["sid"] for r in rows}):
        rr=[r for r in rows if r["sid"]==sid]
        patient_delta[sid]=sum(r["new_pg"]==r["GT"] for r in rr)-sum(r["baseline_pg"]==r["GT"] for r in rr)
    wins=sum(v>0 for v in patient_delta.values());losses=sum(v<0 for v in patient_delta.values());ties=sum(v==0 for v in patient_delta.values())
    roles=Counter()
    role_rescue=Counter();role_harm=Counter()
    for r in changed:
        rs=[x for x in r["addition_roles"].split(";") if x]
        roles.update(rs)
        if r in rescue:role_rescue.update(rs)
        if r in harm:role_harm.update(rs)
    boot=bootstrap(rows)
    passcrit={
      "net_correct_ge_3":len(rescue)-len(harm)>=3,
      "delta_MCC_ge_0.015":new["MCC"]-base["MCC"]>=.015,
      "falseS_nonincrease":new["falseS"]<=base["falseS"],
      "NS_drop_le_0.02":new["NS"]>=base["NS"]-.02-1e-12,
      "NA_drop_le_0.02":new["NA"]>=base["NA"]-.02-1e-12,
      "rescue_patients_ge_3":len({r["sid"] for r in rescue})>=3,
      "patient_wins_gt_losses":wins>losses,
    }
    summary={
      "status":"PASS",
      "baseline":base,"new":new,
      "delta":{k:new[k]-base[k] for k in ("PA","MCC","falseS_rate","S","NS","NA")},
      "raw_baseline":raw0,"raw_new":raw1,
      "paired":{"rescue":len(rescue),"harm":len(harm),"net":len(rescue)-len(harm),
                "rescue_patients":len({r["sid"] for r in rescue}),"harm_patients":len({r["sid"] for r in harm})},
      "patient":{"wins":wins,"losses":losses,"ties":ties,"deltas":patient_delta},
      "pack":{"changed":len(changed),"judge_invalid_fallback":len(invalid),
              "additions":sum(r["added_n"] for r in rows),"drops":sum(r["dropped_n"] for r in rows),
              "mean_added":float(np.mean([r["added_n"] for r in changed])) if changed else 0,
              "mean_char_delta":float(np.mean([float(r["final_body_chars"])-float(r["baseline_body_chars"]) for r in changed if r["final_body_chars"] is not None])) if changed else 0,
              "roles":dict(roles),"rescue_roles":dict(role_rescue),"harm_roles":dict(role_harm)},
      "bootstrap":boot,
      "preregistered_criteria":passcrit,
      "advance":all(passcrit.values()),
      "api_attempts":len(formal_attempts),"http200":sum(a["http_status"]==200 for a in formal_attempts),
      "cost_cny":sum(a["cost"] for a in formal_attempts),
      "superseded_attempts":len(superseded_attempts),
      "superseded_cost_cny":sum(a["cost"] for a in superseded_attempts),
      "reserved_used":False,
    }
    c.csvwrite(c.OUT/"results.csv",rows)
    c.put(c.OUT/"analysis_final.json",summary)
    write_report(summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))
def write_report(s):
    b=s["baseline"];n=s["new"];p=s["paired"];pk=s["pack"]
    lines=[
      "# 067：Conservative Requirement-Preserving Evidence Packing","",
      "## 主结果","",
      "| Method | Correct | PA | MCC | false-S | S / NS / NA recall |",
      "|---|---:|---:|---:|---:|---|",
      f'| Baseline T-S+PriorG | {b["correct"]}/{b["n"]} | {b["PA"]:.2%} | {b["MCC"]:.4f} | {b["falseS"]} | {b["S"]:.2%} / {b["NS"]:.2%} / {b["NA"]:.2%} |',
      f'| 067 Conservative Pack + T-S+PriorG | {n["correct"]}/{n["n"]} | {n["PA"]:.2%} | {n["MCC"]:.4f} | {n["falseS"]} | {n["S"]:.2%} / {n["NS"]:.2%} / {n["NA"]:.2%} |',
      "",
      f'- Paired rescue / harm / net: **{p["rescue"]} / {p["harm"]} / {p["net"]:+d}**.',
      f'- Patient wins / losses / ties: **{s["patient"]["wins"]} / {s["patient"]["losses"]} / {s["patient"]["ties"]}**.',
      f'- Changed packs: {pk["changed"]}/236; additions={pk["additions"]}, drops={pk["drops"]}; invalid final Judge fallback={pk["judge_invalid_fallback"]}.',
      f'- Mean character increase among changed packs: {pk["mean_char_delta"]:.1f}.',
      f'- API: {s["api_attempts"]} attempts, {s["http200"]} HTTP200, cost about ¥{s["cost_cny"]:.4f}.',
      "",
      "## Preregistered criteria","",
      json.dumps(s["preregistered_criteria"],ensure_ascii=False,indent=2),
      "",
      f'**Advance = {s["advance"]}.**',
      "",
      "## Bootstrap","",
      json.dumps(s["bootstrap"],ensure_ascii=False,indent=2),
      "",
      "## Addition roles","",
      json.dumps({"all":pk["roles"],"rescue":pk["rescue_roles"],"harm":pk["harm_roles"]},ensure_ascii=False,indent=2),
      "",
      "## Boundary","",
      "- 067 decisions are GT-blind and evaluated on 052, a different claim batch from the 066 oracle diagnosis.",
      "- 052 is still development, not an external confirmation set.",
      "- No retrieval outside frozen C48 is introduced; Frozen PriorG is unchanged.",
    ]
    (c.OUT/"report_final.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

if __name__=="__main__":main()
