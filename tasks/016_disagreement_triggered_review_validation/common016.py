"""Frozen C48 and existing judge/parser/evaluator reuse; no calls or key loads on import."""
from pathlib import Path
import sys
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/016_disagreement_triggered_review_validation'
sys.path.insert(0,str(ROOT/'tasks/014_qwen27b_baseline_comparison'))
sys.path.insert(0,str(ROOT/'tasks/015_disagreement_adjudication'))
sys.path.insert(0,str(ROOT/'tasks/009_retrieval_baselines'))
import common014 as old14
import common015 as old15
import study009 as baseline
from common014 import (canonical,fingerprint,file_hash,require,save,load_accounts,balance_exhausted,
    now,read,csvrows,jsonlines,write_json,write_lines,write_csv,check_hashes,pilot,sf,evaluate,paired_compare,LABELS)
from prepare_experiment import embedding_jobs

V4=old14.V4
QWEN=old14.MODEL
ROLES=('v4_first','qwen','v4_repeat','independent_review')
RAW=baseline.RAW
NATIVE=baseline.native

def patient_ids(phase):
    order=baseline.patient_order()
    require(phase=='stage1','Only the six-patient stage1 is authorized')
    return order[24:30]

def seal(out,dependencies=(),code=()):
    write_json(out/'manifest.json',dict(created_utc=now(),
        files={p.relative_to(ROOT).as_posix():file_hash(p) for p in out.rglob('*') if p.is_file()},
        dependencies={p.relative_to(ROOT).as_posix():file_hash(p) for p in dependencies},
        code_sha256={p.relative_to(ROOT).as_posix():file_hash(p) for p in code}))

def check_manifest(folder):
    m=read(Path(folder)/'manifest.json')
    for key in ('files','dependencies','code_sha256'):check_hashes(m[key])
    return m

def execution_code():
    paths=[TASK/n for n in ('common016.py','run016.py','prepare016.py','build016.py','io016.py','decisions016.py','budget016.py')]+[
        old14.TASK/'common014.py',old15.TASK/'common015.py',baseline.TASK/'study009.py',
        ROOT/'tasks/004_event_alignment_pilot/pilot.py',ROOT/'tasks/004_event_alignment_pilot/siliconflow.py',
        ROOT/'src/verifact_research/inference/siliconflow_pool.py']
    paths += [ROOT/'tasks/008_retrieval_planning'/n for n in ('common.py','services.py','planning_core.py','build_stages.py','prepare_experiment.py')]
    paths += list((ROOT/'src/verifact_research/evaluation').glob('*.py'))
    return paths

def judge_body(item,reference,prompts,role):
    require(role in ROLES,'Unknown role')
    body=baseline.prior_stages.judge_body(item,reference,prompts)
    if role=='qwen':body['model']=QWEN
    if role=='independent_review':body=old15.build_body(body,item['proposition_id'],'','', 'evidence_only')
    require(set(pilot.strict_json(body['messages'][1]['content']))=={'proposition','reference'},'Judge payload leakage')
    return body

def bound(job):
    if job['kind']!='chat':return NATIVE.bound(job)
    output_rate=12 if job['body']['model']==QWEN else 9
    return ((len(canonical(job['body']).encode())+2000)*3+job['body']['max_tokens']*output_rate)/1e6

def cost(job,tr):
    if job['kind']!='chat' or job['body']['model']==V4:return NATIVE.cost(job,tr)
    return old14.cost(job,tr)

def normalize(job,receipt):
    return old14.normalize(job,receipt,model=job['body']['model'])

def hash_rank(pid,namespace='016/hash-review/v1:'):
    return hashlib.sha256((namespace+pid).encode()).hexdigest()
