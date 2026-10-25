"""Verify019 bindings, snapshot history, and register one80-CNY020 budget."""
from pathlib import Path
import json,subprocess,sys
import common020 as c

def authorize():
    c.require(not (c.OUT/'authority.json').exists(),'Already authorized')
    h=c.read(c.ROOT/'outputs/019_support_boundary_screen/handoff_001.json')
    for name,digest in h['sha256'].items():c.require(c.file_hash(c.ROOT/name)==digest,'019 changed since handoff: '+name)
    jobs=c.jsonlines(c.ROOT/'outputs/019_support_boundary_screen/selection/preparation/jobs.jsonl')
    ledger=c.read(c.ROOT/'outputs/019_support_boundary_screen/live_ledger.json');n=0
    for j in jobs:
        s=ledger['phases']['selection']['jobs'][j['request_id']];ok=[]
        for ptr in s['receipts']:
            p=c.ROOT/'outputs/019_support_boundary_screen'/ptr['file'];c.require(c.file_hash(p)==ptr['sha256'],'019 receipt changed')
            r=c.read(p);c.require(r['job_sha256']==c.fingerprint(j) and r['actual_body']==j['body'],'019 request binding')
            if r['transport']['http_status']==200:ok.append(r)
        c.require(len(ok)==1,'019 duplicate/missing response')
        parsed=c.prior.parse(ok[0]['transport'],j['arm']=='S');c.require(parsed['status']=='success','019 parse failure');n+=1
    c.write_json(c.OUT/'019_preflight_check.json',dict(checked_files=len(h['sha256']),bound_formal_answers=n,passed=True,independent_audit=False,new_API_calls=0))
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=c.ROOT).decode().split('\0')
    paths={c.ROOT/n for n in tracked if n and (c.ROOT/n).is_file()}
    paths.update(c.ROOT/n for n in h['sha256'])
    c.write_json(c.OUT/'history_before.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in paths}))
    prep=c.OUT/'new10/preparation_002';c.check_manifest(prep)
    inputs=c.jsonlines(prep/'inputs.jsonl');corpus=c.jsonlines(prep/'corpus.jsonl')
    embed=sum(c.bound(j) for j in c.jsonlines(prep/'jobs.jsonl'))
    rerank=sum(((max((len(p['search_text'].encode()) for p in corpus if p['subject_id']==r['subject_id']),default=0)+len(r['text'].encode())+256)*80+2000)*.07/1e6 for r in inputs)
    judge=sum((sum(len(m['content']) for m in c.body(r['text'],'X'*8160,scored)['messages'])*.35*3+500*9)/1e6 for r in inputs for scored in (False,True))*2
    expected=embed+rerank+judge+8;c.require(expected<=c.CAP,'Whole020 forecast exceeds80')
    accounts=[a for a in c.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    cfg=c.load_config(c.ROOT/'.env.aliyun');c.require(accounts and accounts[0].alias=='account_2' and cfg.api_key,'Missing configured credentials')
    code=list(c.TASK.glob('*.py'))+[c.TASK/'README.md',c.OUT/'protocol_001.md']
    code += [Path(m.__file__) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and str(c.ROOT) in m.__file__ and m.__file__.endswith('.py')]
    c.write_json(c.OUT/'authority.json',dict(created_utc=c.now(),authorization='User explicitly requested execution020; SiliconFlow enabled pool then one Alibaba key;80 CNY whole task',
        cap_cny=80,expected_whole_task_cny=expected,judge_estimate_cny=judge,embedding_upper_cny=embed,rerank_upper_cny=rerank,failure_allowance_cny=8,
        accounts=[a.alias for a in accounts],SF_model=c.MODEL,Alibaba_model=c.ALI_MODEL,Alibaba_endpoint=cfg.endpoint,
        prices=dict(chat_input=3,chat_output=9,BGE_input=.07,unit='CNY per million tokens',basis='conservative peak no-cache'),
        price_sources_checked_20260918=['https://docs.siliconflow.cn/docs/release-notes/overview','https://siliconflow.cn/pricing','https://help.aliyun.com/zh/model-studio/deepseek-v4-flash'],
        sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in set(code)}))
    c.write_json(c.OUT/'CURRENT.md.json',dict(status='prepared_for_execution',claims=879,rounds=2,lambda_value=2,remaining_test_patients=40,independent_audit=False))
    print('AUTHORIZATION_REGISTERED',round(expected,4),'CNY; hard cap80; no keys printed;019 bound',n,flush=True)

if __name__=='__main__':authorize()
