"""One night-window API ledger, shared across stages and including unknown attempts."""
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime,timezone
import json,math,msvcrt,threading,time,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from verifact_research.inference.aliyun import load_config,AliyunClient,chat_body
LOCK=threading.Lock();P=ROOT/'.local_models/night_20261031'

def read_ledger():
    path=P/'api_ledger.jsonl'
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()] if path.exists() else []

@contextmanager
def locked():
    P.mkdir(parents=True,exist_ok=True)
    with LOCK:
        with (P/'api.lock').open('a+b') as file:
            file.seek(0,2)
            if not file.tell():file.write(b'0');file.flush()
            file.seek(0);msvcrt.locking(file.fileno(),msvcrt.LK_LOCK,1)
            try:yield
            finally:file.seek(0);msvcrt.locking(file.fileno(),msvcrt.LK_UNLCK,1)

def append(event):
    with (P/'api_ledger.jsonl').open('a',encoding='utf-8') as file:
        file.write(json.dumps(event,ensure_ascii=False)+'\n');file.flush()

def send(messages,folder,*,max_tokens=2048,task='147_fixed_reason',json_mode=True):
    cfg=load_config(ROOT/'.env.aliyun');body=chat_body(cfg,messages,max_tokens=max_tokens)
    if json_mode:body['response_format']={'type':'json_object'}
    # UTF-8 byte count is a deliberately conservative token allowance for this small text request.
    input_bound=len(json.dumps(body,ensure_ascii=False).encode('utf-8'))+256
    reservation=max(.05,math.ceil(((input_bound*3+max_tokens*9)/1_000_000+.01)*100)/100)
    client=AliyunClient(cfg,timeout=120);client.validate(body)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    attempt=folder.relative_to(ROOT).as_posix()
    with locked():
        session=json.loads((P/'session.json').read_text())
        if time.time()+30>=session['end_epoch']:raise TimeoutError('Night API window ended')
        used=sum(r['reservation_CNY'] for r in read_ledger() if r.get('event')=='reserved')
        if used+reservation>80:raise RuntimeError('Whole night API cap80 would be exceeded')
        append(dict(event='reserved',attempt=attempt,task=task,reservation_CNY=reservation,
                    cumulative_reserved_CNY=used+reservation,epoch=time.time(),max_tokens=max_tokens))
    (folder/'request.json').write_text(json.dumps(body,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    start=time.perf_counter();transport=client.send(body);elapsed=time.perf_counter()-start
    (folder/'receipt.json').write_text(json.dumps(transport,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    try:native=json.loads(transport['body_text'])
    except ValueError:native={}
    if not isinstance(native,dict):native={}
    usage=native.get('usage') or {};estimate=None
    if isinstance(usage.get('prompt_tokens'),int) and isinstance(usage.get('completion_tokens'),int):
        estimate=(usage['prompt_tokens']*3+usage['completion_tokens']*9)/1_000_000
    with locked():append(dict(event='received',attempt=attempt,task=task,http_status=transport['http_status'],
        outcome_unknown=transport['outcome_unknown'],usage=usage,estimated_CNY_peak_no_discount=estimate,
        seconds=elapsed,epoch=time.time(),reservation_released=False))
    return native,transport,elapsed
