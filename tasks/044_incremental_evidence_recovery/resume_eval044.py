"""Resume only the already-frozen 044 eval_score jobs. No method regeneration."""
import concurrent.futures,hashlib,json,os,sys
from collections import Counter,deque
from pathlib import Path
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/044_incremental_evidence_recovery"
JOBS=OUT/"eval_score/jobs.jsonl"
CAP=80.0
PRICES={"deepseek":(3,9),"qwen":(3,12)}

sys.path.insert(0,str(ROOT/"tasks/024_lambda2_transfer_validation"))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import Config,load_config

def now():return datetime.now(timezone.utc).isoformat()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def digest(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def lines(p):
    with Path(p).open(encoding="utf-8-sig") as f:return [json.loads(x) for x in f if x.strip()]
def put(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf-8",newline="\n") as f:f.write(json.dumps(v,ensure_ascii=False,indent=2)+"\n")
def bound(job):
    ip,op=PRICES[job["model_key"]];b=job["body"]
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",2048)*op)/1e6
def charge(job,tr):
    if tr and tr.get("http_status")==200:
        try:
            u=json.loads(tr["body_text"])["usage"];i=int(u["prompt_tokens"]);o=int(u["completion_tokens"])
            ip,op=PRICES[job["model_key"]];return (i*ip+o*op)/1e6
        except Exception:pass
    return bound(job)

def target_state(jobs):
    terminal={};counts=Counter();unresolved=[]
    for k,j in enumerate(jobs,1):
        rid=j["request_id"];prefix=digest(rid)[:24];hits=[]
        for num in (1,2,3):
            d=OUT/"attempts"/f"{prefix}_{num:02}"
            if d.exists():hits.append(d)
        counts[rid]=len(hits)
        for d in hits:
            rp=d/"receipt.json"
            if not rp.exists():
                unresolved.append((rid,str(d)));continue
            tr=read(rp)["transport"]
            if tr.get("http_status")==200:
                if rid in terminal:raise RuntimeError("duplicate HTTP200 "+rid)
                terminal[rid]=(tr,j,d/"request.json")
        if k%300==0:print("indexed",k,"terminal",len(terminal),"unresolved",len(unresolved),flush=True)
    return terminal,counts,unresolved

def main():
    jobs=lines(JOBS);terminal,counts,unknown=target_state(jobs);ids={j["request_id"] for j in jobs}
    unknown_ids={r for r,_ in unknown}
    nonterminal=[r for r in ids if r not in terminal and counts[r] and r not in unknown_ids]
    if nonterminal:raise RuntimeError("target jobs have nonterminal prior attempts: "+str(nonterminal[:5]))
    # Never repeat request files with no receipt: outcome is unknown.
    pending=[j for j in jobs if j["request_id"] not in terminal and counts[j["request_id"]]==0]
    # train_audit execution cost is cumulative through train_score + train_audit.
    used=float(read(OUT/"train_audit/execution_001.json")["used_cny"])
    for rid,(tr,j,_) in terminal.items():used+=charge(j,tr)
    unknown_reserve=0.0
    for rid,d in unknown:
        rq=read(Path(d)/"request.json");unknown_reserve+=float(rq["reservation_cny"])
    used+=unknown_reserve
    print("frozen jobs",len(jobs),"terminal",sum(r in terminal for r in ids),"unknown",len(unknown_ids),
          "never_sent_pending",len(pending),"used_plus_unknown_reserve",round(used,6),flush=True)
    if not pending:return
    cfg=load_config(ROOT/".env.aliyun");client=DirectClient(Config(cfg.api_key,cfg.base_url,"deepseek-v4-flash-0731"),timeout=180)
    for j in pending:
        if j["model_key"]!="deepseek" or j["body"]["model"]!="deepseek-v4-flash-0731":raise RuntimeError("unexpected eval model")
        client.validate(j["body"])
    lock=OUT/"resume_eval.lock";fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
    q=deque(pending);inflight={};reserved=0.;done=0
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            while q or inflight:
                while q and len(inflight)<8:
                    j=q.popleft();reserve=bound(j)
                    if used+reserved+reserve>CAP:raise RuntimeError("budget80")
                    num=counts[j["request_id"]]+1
                    dst=OUT/"attempts"/f"{digest(j['request_id'])[:24]}_{num:02}"
                    if dst.exists():raise RuntimeError("attempt collision")
                    dst.mkdir(parents=True)
                    req=dict(created_utc=now(),stage="eval_score",job=j,attempt=num,
                      body_sha256=digest(j["body"]),reservation_cny=reserve,prior_used_reserved=used+reserved,cap=CAP,
                      recovery_note="resume frozen eval_score after interrupted runner; no job/body changes")
                    put(dst/"request.json",req);counts[j["request_id"]]+=1;reserved+=reserve
                    fut=pool.submit(client.send,j["body"]);inflight[fut]=(j,dst,reserve)
                ready,_=concurrent.futures.wait(inflight,timeout=10,return_when=concurrent.futures.FIRST_COMPLETED)
                for fut in ready:
                    j,dst,reserve=inflight.pop(fut);reserved-=reserve
                    try:tr=fut.result()
                    except Exception as exc:
                        tr=dict(http_status=0,body_text="",headers={},outcome_unknown=True,started_utc=now(),ended_utc=now(),exception_type=type(exc).__name__)
                    put(dst/"receipt.json",dict(request_sha256=sha(dst/"request.json"),transport=tr))
                    amount=charge(j,tr);used+=amount;done+=1
                    if tr.get("http_status")!=200:raise RuntimeError("non200/unknown during recovery "+str(tr.get("http_status")))
                    returned=json.loads(tr["body_text"]).get("model")
                    if returned!="deepseek-v4-flash-0731":raise RuntimeError("unexpected returned model")
                    if done%50==0:print("resumed",done,"remaining",len(q)+len(inflight),"used",round(used,4),flush=True)
        put(OUT/"eval_score"/"recovery_001.json",dict(completed_utc=now(),resumed_now=done,total_frozen_jobs=len(jobs),
          cumulative_cost_estimate_cny=used,job_file_sha256=sha(JOBS)))
        print("RESUME COMPLETE",done,"cumulative",round(used,6),flush=True)
    finally:
        if lock.exists():lock.unlink()
if __name__=="__main__":main()
