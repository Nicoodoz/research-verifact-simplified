from pathlib import Path
from collections import Counter
import json,sys,numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"tasks/065_verification_evidence_construction"))
import common065 as c
import run065

LABELS=("Supported","Not Supported","Not Addressed")
def unpack(term,rid):
    if not rid or rid not in term:return {"valid":False,"raw":None,"scores":None,"reason":None,"checks":[]}
    p=term[rid]["parsed"];good=p.get("status") in ("valid","valid_with_format_anomaly") and p.get("verdict") in LABELS
    obj=p.get("parsed") or {}
    return {"valid":bool(good),"raw":p.get("verdict") if good else None,
            "scores":p.get("scores"),"reason":obj.get("reason"),"checks":obj.get("checks") or []}

def mcc(y,p):
    M=np.zeros((3,3),float)
    li={x:i for i,x in enumerate(LABELS)}
    for a,b in zip(y,p):M[li[a],li[b]]+=1
    s=M.sum();cc=np.trace(M);a=M.sum(1);b=M.sum(0)
    d=((s*s-a@a)*(s*s-b@b))**.5
    return float((cc*s-a@b)/d) if d else 0.0
def metrics(rows,key):
    rr=[x for x in rows if x[key] in LABELS]
    y=[x["GT"] for x in rr];p=[x[key] for x in rr]
    out={"n":len(rr),"correct":sum(a==b for a,b in zip(y,p)),
         "PA":sum(a==b for a,b in zip(y,p))/len(rr) if rr else 0,
         "MCC":mcc(y,p) if rr else 0,
         "falseS":sum(a!="Supported" and b=="Supported" for a,b in zip(y,p))}
    for lab in LABELS:
        den=sum(a==lab for a in y)
        out["recall_"+lab.replace(" ","_")]=sum(a==lab and b==lab for a,b in zip(y,p))/den if den else None
    return out

def paired(rows,new,base):
    rr=[x for x in rows if x[new] in LABELS and x[base] in LABELS]
    rescue=[x for x in rr if x[base]!=x["GT"] and x[new]==x["GT"]]
    harm=[x for x in rr if x[base]==x["GT"] and x[new]!=x["GT"]]
    return {"n":len(rr),"rescue":len(rescue),"harm":len(harm),"net":len(rescue)-len(harm),
            "rescue_patients":len({x["sid"] for x in rescue}),
            "rescue_ids":[x["id"] for x in rescue],"harm_ids":[x["id"] for x in harm]}
def main():
    blind={x["id"]:x for x in c.lines(c.OUT/"screen_cases_blind.jsonl")}
    source={x["id"]:x for x in c.lines(c.R044/"planning_001/eval_cases.jsonl")}
    mapping={(x["id"],x["condition"]):x for x in c.lines(c.OUT/"final_mapping.jsonl")}
    attempts,term=run065.state()
    rows=[]
    for pid,x in blind.items():
        gt=source[pid]["GT"];h=c.stable("",pid)[:24]
        A=unpack(term,"065_A_"+h)
        out={"id":pid,"sid":x["sid"],"author":x["author"],"type":x["type"],"GT":gt,
             "A":A["raw"],"A_valid":A["valid"]}
        for cond in ("B","C"):
            mp=mapping[(pid,cond)];z=unpack(term,mp.get("judge_request_id"))
            out[cond]=z["raw"];out[cond+"_valid"]=z["valid"]
            out[cond+"_passages"]=mp["passage_n"];out[cond+"_chars"]=mp["reference_chars"]
            out[cond+"_external"]=mp["external_kept"]
            extset={p for p in mp.get("kept_pids",[]) if p not in set(x["c48_candidate_ids"])}
            extpos={i+1 for i,p in enumerate(mp.get("kept_pids",[])) if p in extset}
            cited=[e for ck in z["checks"] for e in ck.get("evidence_ids",[]) if isinstance(e,int)]
            out[cond+"_external_cited"]=bool(extpos & set(cited))
        rows.append(out)
    common=[x for x in rows if x["A_valid"] and x["B_valid"] and x["C_valid"]]
    fullA=[x for x in rows if x["A_valid"]]
    summary={"A_full":metrics(fullA,"A"),"common_n":len(common)}
    for arm in ("A","B","C"):summary[arm]=metrics(common,arm)
    summary["B_vs_A"]=paired(common,"B","A")
    summary["C_vs_A"]=paired(common,"C","A")
    summary["C_vs_B"]=paired(common,"C","B")
    summary["falseS_delta_BA"]=summary["B"]["falseS"]-summary["A"]["falseS"]
    summary["falseS_delta_CA"]=summary["C"]["falseS"]-summary["A"]["falseS"]
    for name,mask in (
        ("boundary",lambda x:x["type"]=="boundary"),
        ("stable",lambda x:x["type"]=="stable"),
        ("human",lambda x:x["author"]=="human"),
        ("llm",lambda x:x["author"]=="llm")):
        rr=[x for x in common if mask(x)]
        summary[name]={arm:metrics(rr,arm) for arm in ("A","B","C")}
        summary[name]["B_vs_A"]=paired(rr,"B","A")
        summary[name]["C_vs_A"]=paired(rr,"C","A")
    maps=[x for x in c.lines(c.OUT/"final_mapping.jsonl") if x.get("composer_status")=="valid"]
    stats={}
    for arm in ("B","C"):
        mm=[x for x in maps if x["condition"]==arm]
        stats[arm]={"valid_n":len(mm),
                    "mean_passages":float(np.mean([x["passage_n"] for x in mm])),
                    "mean_chars":float(np.mean([x["reference_chars"] for x in mm])),
                    "external_kept_total":int(sum(x["external_kept"] for x in mm))}
    stats["C_external_cited_cases"]=sum(x["C_external_cited"] for x in common)
    summary["evidence_stats"]=stats

    Bpass=(summary["B_vs_A"]["rescue"]>=3 and summary["B_vs_A"]["net"]>=2 and
           summary["B_vs_A"]["harm"]<=1 and summary["falseS_delta_BA"]<=0 and
           summary["B_vs_A"]["rescue_patients"]>=2)
    Cpass=(summary["C_vs_A"]["rescue"]>=3 and summary["C_vs_A"]["net"]>=2 and
           summary["C_vs_A"]["harm"]<=1 and summary["falseS_delta_CA"]<=0 and
           summary["C_vs_A"]["rescue_patients"]>=2)
    Cretr=(summary["C_vs_B"]["rescue"]>=2 and summary["C_vs_B"]["net"]>=1 and
           summary["C_vs_B"]["harm"]<=1)
    summary["decision"]={"B_pass":bool(Bpass),"C_pass":bool(Cpass),"C_incremental_retrieval":bool(Cretr)}
    summary["cost_cny"]=sum(a["cost"] for a in attempts)
    summary["api_attempts"]=len(attempts);summary["http200"]=sum(a["http_status"]==200 for a in attempts)
    c.csvwrite(c.OUT/"results.csv",rows);c.put(c.OUT/"analysis.json",summary)
    write_report(summary,rows)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
def fmt(m):
    return f'{m["correct"]}/{m["n"]} ({100*m["PA"]:.1f}%), MCC {m["MCC"]:.3f}, false-S {m["falseS"]}, recalls {100*m["recall_Supported"]:.1f}/{100*m["recall_Not_Supported"]:.1f}/{100*m["recall_Not_Addressed"]:.1f}%'

def write_report(s,rows):
    md=["# 065 Screen Result","",
        f'共同有效三臂：**{s["common_n"]}/24**；A完整有效：{s["A_full"]["n"]}/24。',"",
        "## 主结果","",
        "| Arm | correct/PA | MCC | false-S | S/NS/NA recall |",
        "|---|---:|---:|---:|---|"]
    for arm in ("A","B","C"):
        m=s[arm]
        md.append(f'| {arm} | {m["correct"]}/{m["n"]} ({100*m["PA"]:.1f}%) | {m["MCC"]:.3f} | {m["falseS"]} | {100*m["recall_Supported"]:.1f}/{100*m["recall_Not_Supported"]:.1f}/{100*m["recall_Not_Addressed"]:.1f}% |')
    md+=["","## Paired","",
         f'- B vs A: {s["B_vs_A"]["rescue"]} rescue / {s["B_vs_A"]["harm"]} harm / net {s["B_vs_A"]["net"]:+d}; rescue patients {s["B_vs_A"]["rescue_patients"]}.',
         f'- C vs A: {s["C_vs_A"]["rescue"]} / {s["C_vs_A"]["harm"]} / net {s["C_vs_A"]["net"]:+d}; rescue patients {s["C_vs_A"]["rescue_patients"]}.',
         f'- C vs B: {s["C_vs_B"]["rescue"]} / {s["C_vs_B"]["harm"]} / net {s["C_vs_B"]["net"]:+d}.',
         f'- false-S delta B-A={s["falseS_delta_BA"]:+d}; C-A={s["falseS_delta_CA"]:+d}.',"",
         "## Evidence pack","",
         f'- B mean passages {s["evidence_stats"]["B"]["mean_passages"]:.2f}, mean chars {s["evidence_stats"]["B"]["mean_chars"]:.0f}.',
         f'- C mean passages {s["evidence_stats"]["C"]["mean_passages"]:.2f}, mean chars {s["evidence_stats"]["C"]["mean_chars"]:.0f}, external passages kept total {s["evidence_stats"]["C"]["external_kept_total"]}.',
         f'- C final Judge cited external evidence in {s["evidence_stats"]["C_external_cited_cases"]}/{s["common_n"]} common-valid cases.',"",
         "## Decision","",
         f'- B focus-only passes prereg screen: **{s["decision"]["B_pass"]}**',
         f'- C retrieve+focus passes prereg screen: **{s["decision"]["C_pass"]}**',
         f'- C has incremental retrieval value over B: **{s["decision"]["C_incremental_retrieval"]}**',"",
         f'API cost: ¥{s["cost_cny"]:.6f}; attempts {s["api_attempts"]}, HTTP200 {s["http200"]}.']
    (c.OUT/"report.md").write_text("\n".join(md)+"\n",encoding="utf-8")

if __name__=="__main__":main()
