"""One explicitly requested, non-clinical availability probe; no retries or experiment resume."""
from pathlib import Path
from datetime import datetime
import sys
import time
import urllib.request
import urllib.error
import json

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tasks/016_disagreement_triggered_review_validation'))
import common016 as c
from verifact_research.inference.siliconflow_pool import NoRedirect

out=Path(__file__).resolve().parent
body=dict(model=c.QWEN,messages=[dict(role='user',content='Reply with exactly OK.')],temperature=0,max_tokens=32,enable_thinking=False,stream=False)
carry_path=c.OUT/'v4_completion_001/live/ledger.json'
carry=c.read(carry_path)['used_or_reserved_cny']
bound=((len(c.canonical(body).encode())+2000)*3+32*12)/1e6
c.require(carry+bound<=40,'016 cumulative budget exhausted')
c.write_json(out/'request.json',body)
c.write_json(out/'authorization.json',dict(created_utc=c.now(),source='User explicitly requests one simple Qwen service availability test only',
    attempts_allowed=1,timeout_seconds=45,no_clinical_text=True,no_016_experiment_resume=True,
    prior_task_used_or_reserved_cny=carry,carry_source=carry_path.relative_to(ROOT).as_posix(),carry_sha256=c.file_hash(carry_path),
    probe_max_reservation_cny=bound,task_cap_cny=40,price_basis='Same-day verified SiliconFlow public Qwen input3/output12 CNY per million; not invoice'))
accounts=[a for a in c.load_accounts(ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
c.require(accounts and accounts[0].alias=='account_2','Account_2 required')
a=accounts[0];start=c.now();clock=time.monotonic();error=None
req=urllib.request.Request(c.NATIVE.ENDPOINTS['chat'],data=c.canonical(body).encode(),method='POST',headers={'Authorization':'Bearer '+a.key,'Content-Type':'application/json'})
try:
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=45) as response:
        status=response.status;text=response.read().decode('utf-8',errors='replace')
except urllib.error.HTTPError as exc:
    status=exc.code;text=exc.read().decode('utf-8',errors='replace');error=type(exc).__name__
except (OSError,urllib.error.URLError) as exc:
    status=0;text='';error=type(exc).__name__
elapsed=time.monotonic()-clock;ended=c.now()
for account in accounts:text=text.replace(account.key,'[REDACTED_API_KEY]')
c.write_json(out/'receipt.json',dict(account=a.alias,request_sha256=c.fingerprint(body),http_status=status,body_text=text,
    started_utc=start,ended_utc=ended,latency_seconds=elapsed,error_type=error,outcome_unknown=status==0))
answer=None;usage=None;model=None;finish=None;fee=bound;basis='unknown_usage_reservation'
try:
    native=c.pilot.strict_json(text);usage=native['usage'];model=native.get('model')
    answer=native['choices'][0]['message'].get('content');finish=native['choices'][0]['finish_reason']
    p=usage['prompt_tokens'];o=usage['completion_tokens']
    c.require(type(p) is int and type(o) is int and p>=0 and o>=0 and usage['total_tokens']==p+o,'Invalid usage')
    fee=(p*3+o*12)/1e6;basis='public_price_usage_estimate_not_invoice'
except (ValueError,KeyError,IndexError,TypeError):pass
ok=status==200 and model==c.QWEN and finish=='stop' and isinstance(answer,str) and answer.strip()=='OK'
result=dict(checked_utc=ended,model_requested=c.QWEN,model_returned=model,http_status=status,latency_seconds=elapsed,
    availability_probe_passed=ok,answer=answer,finish_reason=finish,error_type=error,usage=usage,
    probe_cost_or_reserved_cny=fee,cost_basis=basis,task_total_cost_or_reserved_cny=carry+fee,
    task_cap_cny=40,requests_sent=1,retries=0,clinical_text_sent=False,experiment_resumed=False,
    limitation='One short prompt only; does not establish long-context or batch stability.')
c.write_json(out/'result.json',result)
print(c.canonical(result))
