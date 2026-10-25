"""Blind reason audit for the only three eval claims where frozen learned selector changed the reference."""
from pathlib import Path
import sys,json,hashlib,os,re
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/044_incremental_evidence_recovery"
DEST=OUT/"eval_audit_recovery_001"
MODEL="qwen3.8-27b"
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config

def now():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def digest(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def entries(ref):
    starts=list(re.finditer(r"(?m)^(\d+)\. Date:",ref))
    return {int(m.group(1)):ref[m.start():(starts[i+1].start() if i+1<len(starts) else len(ref))] for i,m in enumerate(starts)}
def quote_ok(q,text):
    if not isinstance(q,str) or not q.strip():return False
    pat=r"\s+".join(re.escape(x) for x in q.split())
    return re.search(pat,text) is not None
def main():
    if DEST.exists():raise RuntimeError("audit recovery exists")
    choices=[x for x in lines(OUT/"model/eval_choices.jsonl") if x["choice"]!="base"]
    assert len(choices)==3
    cases={x["id"]:x for x in lines(OUT/"planning_001/eval_cases.jsonl")}
    rows=read(OUT/"results_recovery_001/score_rows.json")
    by={(x["id"],x["condition"],x["round"]):x for x in rows}
    template=lines(OUT/"train_audit/jobs.jsonl")[0]["body"]
    system=template["messages"][0]["content"]
    jobs=[]
    for ch in choices:
        x=cases[ch["id"]]
        for cond in ("base","learned"):
            r=by[(ch["id"],cond,0)]
            if not r.get("Score"):continue
            ref=x["base"] if cond=="base" else x["packs"][ch["choice"]]["reference"]
            payload={"proposition":x["claim"],"reference":ref,"rationale":{"reason":r.get("reason"),"checks":r.get("checks")}}
            body={"model":MODEL,"messages":[{"role":"system","content":system},{"role":"user","content":json.dumps(payload,ensure_ascii=False)}],
                  "temperature":0,"max_tokens":800,"enable_thinking":False,"response_format":{"type":"json_object"}}
            jobs.append(dict(id=x["id"],condition=cond,final_label=r["Score"],body=body,reference=ref))
    DEST.mkdir(parents=True);put(DEST/"jobs.json",jobs)
    cfg=load_config(ROOT/".env.aliyun");client=DirectClient(Config(cfg.api_key,cfg.base_url,MODEL),timeout=180)
    results=[];cost=0.
    for k,j in enumerate(jobs,1):
        tr=client.send(j["body"]);rec=DEST/f"receipt_{k:02}.json";put(rec,{"body_sha256":digest(j["body"]),"transport":tr})
        if tr.get("http_status")!=200:
            results.append(dict(id=j["id"],condition=j["condition"],status="invalid",error="no_http200"));continue
        raw=json.loads(tr["body_text"]);u=raw.get("usage",{});cost+=(u.get("prompt_tokens",0)*3+u.get("completion_tokens",0)*12)/1e6
        try:
            obj=json.loads(raw["choices"][0]["message"]["content"]);rl=obj.get("reason_label");el=obj.get("evidence_label")
            gr=obj.get("grounding");cv=obj.get("coverage");cts=obj.get("citations",[])
            valid_core=rl in ("Supported","Not Supported","Not Addressed","Mixed","Unclear") and el in ("Supported","Not Supported","Not Addressed","Uncertain") and gr in ("full","partial","none","uncertain") and cv in ("complete","partial","uncertain") and isinstance(cts,list)
            lookup=entries(j["reference"]);citation_valid=True
            for c in cts:
                rid=c.get("reference_id");q=c.get("quote")
                if not isinstance(rid,int) or rid not in lookup or not quote_ok(q,lookup[rid]):citation_valid=False
            joint=bool(valid_core and rl==j["final_label"] and el==j["final_label"] and gr=="full" and cv=="complete" and citation_valid)
            results.append(dict(id=j["id"],condition=j["condition"],status="valid" if valid_core else "invalid",
              final_label=j["final_label"],reason_label=rl,evidence_label=el,grounding=gr,coverage=cv,citation_valid=citation_valid,
              joint_pass=joint,n_citations=len(cts),note=obj.get("note")))
        except Exception as exc:results.append(dict(id=j["id"],condition=j["condition"],status="invalid",error=type(exc).__name__+":"+str(exc)[:160]))
    put(DEST/"results.json",results);put(DEST/"summary.json",dict(created_utc=now(),jobs=len(jobs),cost_cny=cost,
      valid=sum(r["status"]=="valid" for r in results),joint_pass=sum(r.get("joint_pass",False) for r in results),results=results))
    print(json.dumps(read(DEST/"summary.json"),ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__":main()
