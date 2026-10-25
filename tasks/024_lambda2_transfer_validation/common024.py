"""024 immutable inputs, Alibaba-only transport accounting, fixed 0/2 decisions."""
from pathlib import Path
import csv, hashlib, json, os, sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/024_lambda2_transfer_validation'
sys.path.insert(0,str(ROOT/'tasks/020_lambda2_patient_validation'))
import common020 as old
from verifact_research.inference.aliyun import Config, AliyunClient, load_config
MODELS={'deepseek':'deepseek-v4-flash-0731','qwen':'qwen3.8-27b'}
PRICES={'deepseek':(3,9),'qwen':(3,12)}
CAP=80.0
canonical=old.canonical
fingerprint=old.fingerprint
file_hash=old.file_hash
require=old.require
read=old.read
lines=old.jsonlines
LABELS=old.LABELS
def now(): return datetime.now(timezone.utc).isoformat()
def put(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
def csvread(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvwrite(p,rs):
    with Path(p).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
def bound(job):
    ip,op=PRICES[job['model_key']]
    return ((len(canonical(job['body']).encode())+2000)*ip+job['body']['max_tokens']*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr['body_text'])['usage'];i,o=u['prompt_tokens'],u['completion_tokens']
        require(type(i) is int and type(o) is int and i>=0 and o>=0,'Invalid usage')
        require(u.get('total_tokens',i+o)==i+o,'Usage total mismatch')
        ip,op=PRICES[job['model_key']]
        return (i*ip+o*op)/1e6,'peak_no_cache_usage_estimate'
    except (ValueError,KeyError,TypeError):
        return bound(job),'unknown_usage_reservation'
def verify_inputs():
    m=read(OUT/'preparation_001/manifest.json')
    for p,h in m['sha256'].items():require(file_hash(ROOT/p)==h,'Frozen input changed: '+p)
    return lines(OUT/'preparation_001/jobs.jsonl')
def load_attempts(jobs):
    byid={j['request_id']:j for j in jobs};attempts=[];terminal={}
    for p in sorted((OUT/'attempts').glob('*/request.json')):
        r=read(p);j=byid[r['request_id']]
        require(r['body']==j['body'] and r['body_sha256']==fingerprint(j['body']),'Request mismatch')
        require(r['reservation_cny']==bound(j),'Reservation mismatch')
        receipt=p.parent/'receipt.json'
        a=dict(request_id=j['request_id'],attempt_dir=p.parent.relative_to(OUT).as_posix(),model_key=j['model_key'],charge_cny=bound(j),charge_basis='unresolved_attempt_reservation',http_status=None)
        if receipt.exists():
            t=read(receipt);require(t['request_sha256']==file_hash(p),'Receipt binding mismatch')
            tr=t['transport'];cost,basis=charge(j,tr)
            a.update(charge_cny=cost,charge_basis=basis,http_status=tr['http_status'])
            if tr['http_status']==200:
                require(j['request_id'] not in terminal,'Duplicate terminal answer')
                parsed=old.prior.parse(tr,j['arm']=='S')
                require(parsed.get('model_returned')==j['body']['model'],'Unexpected returned model')
                terminal[j['request_id']]=parsed
        attempts.append(a)
    return attempts,terminal
