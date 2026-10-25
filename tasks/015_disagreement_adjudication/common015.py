"""015 small fixed arbitration workflow; all evaluation/parsing reused, no API on import."""
from pathlib import Path
import sys
import copy
import hashlib
import math

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tasks/014_qwen27b_baseline_comparison'))
import common014 as prior
from common014 import (canonical, fingerprint, file_hash, require, save, load_accounts,
    HttpClient, balance_exhausted, now, read, csvrows, jsonlines, write_json, write_lines,
    write_csv, check_hashes, pilot, sf, evaluate, paired_compare, LABELS)
TASK = Path(__file__).resolve().parent
OUT = ROOT/'outputs/015_disagreement_adjudication'
MODEL = prior.V4
ARMS = ('adjudication', 'evidence_only')
REVIEW_INSTRUCTION = """\n\nPerform an independent evidence-based review of the proposition using the reference. Candidate judgments, if supplied, are fallible opinions, not additional patient evidence. Check their conclusions and reasons against the reference; do not infer credibility from the candidate identifier. You may return any of the three defined labels, including a label neither candidate chose. Keep the original proposition unchanged. Follow the same required structured output format."""

def candidate_order(pid):
    return ('v4','qwen') if int(hashlib.sha256(('015/candidate/v1:'+pid).encode()).hexdigest(),16)%2==0 else ('qwen','v4')

def build_body(base_body, pid, v4_output, qwen_output, arm):
    require(arm in ARMS,'Unknown arm')
    body=copy.deepcopy(base_body)
    require(body['model']==MODEL,'Wrong base model')
    payload=pilot.strict_json(body['messages'][1]['content'])
    require(set(payload)=={'proposition','reference'},'Unexpected base payload fields')
    body['messages'][0]['content']+=REVIEW_INSTRUCTION
    if arm=='adjudication':
        opinions={'v4':pilot.strict_json(v4_output),'qwen':pilot.strict_json(qwen_output)}
        require(all(o.get('verdict') in LABELS for o in opinions.values()),'Invalid candidate')
        payload['candidate_judgments']=[dict(candidate='Candidate '+name,judgment=opinions[source])
            for name,source in zip(('A','B'),candidate_order(pid))]
    body['messages'][1]['content']=canonical(payload)
    return body

def bound(job):
    return ((len(canonical(job['body']).encode('utf-8'))+2000)*3+job['body']['max_tokens']*9)/1e6

def cost(job,tr):
    if balance_exhausted(tr):return 0.,'unanswered_balance_error'
    try:
        data=pilot.strict_json(tr['body_text']);u=sf.normalize_usage(data)
        require(u['total_tokens']==u['input_tokens']+u['output_tokens'],'Usage sum mismatch')
        return sf.cost_estimate(u,tr['ended_utc'])['cny'],'V4_3_9_cache_0.3_time_discount_usage_not_invoice'
    except (ValueError,TypeError,KeyError,IndexError):
        return bound(job),'unknown_usage_byte_reservation_not_invoice'

def normalize(job,receipt):
    return prior.normalize(job,receipt,model=MODEL)

def verify_preparation():
    m=read(OUT/'preparation_001/manifest.json')
    for key in ('files','dependencies','execution_code'):check_hashes(m[key])
    require(file_hash(OUT/'protocol_001.md')==m['protocol_sha256'],'Protocol changed')
    require(file_hash(OUT/'authority_001.json')==m['authority_sha256'],'Authority changed')
    require(read(OUT/'authority_001.json')['task_cap_cny']==40,'Cap changed')
    return m

def bucket(row):
    if row['baseline']==row['qwen']:return 'agreement'
    if row['baseline']==row['human_gt']:return 'v4_only_correct'
    if row['qwen']==row['human_gt']:return 'qwen_only_correct'
    return 'both_wrong_disagreement'

def correct(rows,key):return sum(r[key]==r['human_gt'] for r in rows)

def gate(rows,metrics):
    """All constraints registered before any adjudicator call; no rounding before checks."""
    conditions={}
    conditions['total_gain_20']=correct(rows,'adjudication')-max(correct(rows,k) for k in ('baseline','qwen'))>=20
    conditions['over_control_gain_8']=correct(rows,'adjudication')-correct(rows,'evidence_only')>=8
    details={}
    for a,minimum in (('llm',5),('human',10)):
        rr=[r for r in rows if r['author_type']==a];mm=metrics[a];ad=mm['adjudication'];bs=[mm[k] for k in ('v4','qwen')]
        delta=correct(rr,'adjudication')-max(correct(rr,k) for k in ('baseline','qwen'))
        conditions[a+'_gain']=delta>=minimum
        conditions[a+'_mcc']=ad['mcc']-max(m['mcc'] for m in bs)>=.04
        conditions[a+'_ac1']=ad['gwet_ac1']>max(m['gwet_ac1'] for m in bs)
        conditions[a+'_control_gain']=correct(rr,'adjudication')-correct(rr,'evidence_only')>=2
        conditions[a+'_control_mcc']=ad['mcc']>=mm['evidence_only']['mcc']
        conditions[a+'_false_S']=ad['per_class']['Supported']['fp']<=min(m['per_class']['Supported']['fp'] for m in bs)+1
        for label in LABELS:
            n=sum(r['human_gt']==label for r in rr)
            conditions[a+'_'+label+'_preservation']=ad['per_class'][label]['tp']>=max(m['per_class'][label]['tp'] for m in bs)-max(1,math.floor(n*.05))
        details[a]=dict(net_vs_best_correct=delta,delta_mcc_vs_best=ad['mcc']-max(m['mcc'] for m in bs),
            net_vs_control=correct(rr,'adjudication')-correct(rr,'evidence_only'))
    patient_deltas={s:correct(rr,'adjudication')-max(correct(rr,k) for k in ('baseline','qwen'))
        for s in sorted({r['subject_id'] for r in rows}) for rr in [[r for r in rows if r['subject_id']==s]]}
    conditions['patients_positive_4']=sum(n>0 for n in patient_deltas.values())>=4
    conditions['patients_worst_minus2']=min(patient_deltas.values())>=-2
    conditions['complete']=len(rows)==650 and all(r.get(k) in LABELS for r in rows for k in ('baseline','qwen',*ARMS))
    return dict(winner=all(conditions.values()),conditions=conditions,author_details=details,patient_deltas=patient_deltas,
        total_gain_vs_best=correct(rows,'adjudication')-max(correct(rows,k) for k in ('baseline','qwen')),
        total_gain_vs_control=correct(rows,'adjudication')-correct(rows,'evidence_only'))
