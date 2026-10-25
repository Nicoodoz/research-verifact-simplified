"""046 append-only API runner with cumulative CNY 8 cap."""
from pathlib import Path
import json,hashlib,os,concurrent.futures,sys
from collections import Counter,deque
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/"outputs/046_requirement_aware_retrieval_screen";CAP=8.0
sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
import core024
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config
MODELS={"deepseek":"deepseek-v4-flash-0731","qwen":"qwen3.8-27b"};PRICES={"deepseek":(3,9),"qwen":(3,12)}
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def dig(v):return hashlib.sha256(canon(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write("\n")
def bound(j):
    ip,op=PRICES[j["model_key"]];b=j["body"];return ((len(canon(b).encode())+2000)*ip+b.get("max_tokens",1500)*op)/1e6
def charge(j,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICES[j["model_key"]]
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(j)
def parse(j,tr):
    if tr.get("http_status")!=200:return {"status":"invalid","errors":["no_http200"]}
    if j["kind"]=="judge":
        p=core024.parse(tr,True)
        if p.get("model_returned") not in (None,MODELS["deepseek"]):p["status"]="invalid_core_fields"
        return p
    try:
        raw=json.loads(tr["body_text"]);obj=json.loads(raw["choices"][0]["message"]["content"])
        if j["kind"] in ("selector","reranker"):
            if not isinstance(obj.get("selected"),list) or len(obj["selected"])>3:raise ValueError("bad selected")
        elif j["kind"]=="planner":
            if not isinstance(obj.get("queries"),list) or len(obj["queries"])>2:raise ValueError("bad queries")
        return {"status":"valid","parsed":obj,"usage":raw.get("usage",{}),"model_returned":raw.get("model")}
    except Exception as e:return {"status":"invalid","errors":[type(e).__name__+":"+str(e)[:180]]}

def state():
    attempts=[];term={};base=OUT/"attempts"
    if not base.exists():return attempts,term
    for p in sorted(base.glob("*/request.json")):
        rq=read(p);j=rq["job"];rp=p.parent/"receipt.json";tr=None
        if rp.exists():tr=read(rp)["transport"]
        amount=charge(j,tr) if tr else float(rq["reservation_cny"])
        attempts.append(dict(request_id=j["request_id"],stage=rq["stage"],model_key=j["model_key"],cost=amount,http_status=tr.get("http_status") if tr else None,path=str(p.relative_to(ROOT))))
        if tr and tr.get("http_status")==200:
            if j["request_id"] in term:raise RuntimeError("duplicate HTTP200 "+j["request_id"])
            term[j["request_id"]]=dict(job=j,transport=tr,parsed=parse(j,tr))
    return attempts,term
def run(stage,workers=6):
    jobs=lines(OUT/f"{stage}_jobs.jsonl");attempts,term=state();used=sum(x["cost"] for x in attempts)
    counts=Counter(x["request_id"] for x in attempts);pending=[]
    for j in jobs:
        if j["request_id"] in term:continue
        if counts[j["request_id"]]:raise RuntimeError("unresolved prior request "+j["request_id"])
        pending.append(j)
    cfg=load_config(ROOT/".env.aliyun");clients={k:DirectClient(Config(cfg.api_key,cfg.base_url,m),timeout=180) for k,m in MODELS.items()}
    for j in pending:
        if j["body"]["model"]!=MODELS[j["model_key"]]:raise RuntimeError("model mismatch")
        clients[j["model_key"]].validate(j["body"])
    lock=OUT/"live.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    q=deque(pending);inflight={};reserved=0.;done=0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            while q or inflight:
                while q and len(inflight)<workers:
                    j=q.popleft();r=bound(j)
                    if used+reserved+r>CAP:raise RuntimeError("budget8")
                    num=counts[j["request_id"]]+1;dst=OUT/"attempts"/f"{dig(j['request_id'])[:24]}_{num:02}"
                    if dst.exists():raise RuntimeError("attempt collision")
                    dst.mkdir(parents=True);put(dst/"request.json",dict(created_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
                      stage=stage,job=j,attempt=num,reservation_cny=r,body_sha256=dig(j["body"]),prior_used_reserved=used+reserved,cap_cny=CAP))
                    counts[j["request_id"]]+=1;reserved+=r
                    f=pool.submit(clients[j["model_key"]].send,j["body"]);inflight[f]=(j,dst,r)
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for f in ready:
                    j,dst,r=inflight.pop(f);reserved-=r
                    try:tr=f.result()
                    except Exception as e:tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,exception_type=type(e).__name__)
                    put(dst/"receipt.json",dict(request_sha256=sha(dst/"request.json"),transport=tr));used+=charge(j,tr);done+=1
                    if tr.get("http_status")!=200:raise RuntimeError("non200 "+str(tr.get("http_status")))
                    if json.loads(tr["body_text"]).get("model")!=MODELS[j["model_key"]]:raise RuntimeError("returned model mismatch")
                    if done%20==0:print(stage,done,"remaining",len(q)+len(inflight),"used",round(used,4),flush=True)
        put(OUT/f"{stage}_execution.json",dict(completed_utc=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
          stage=stage,planned=len(jobs),completed_now=done,cumulative_cost_cny=used))
        print("COMPLETE",stage,len(jobs),"cost",round(used,6),flush=True)
    finally:
        if lock.exists():lock.unlink()
if __name__=="__main__":
    import argparse;ap=argparse.ArgumentParser();ap.add_argument("stage");a=ap.parse_args();run(a.stage)
