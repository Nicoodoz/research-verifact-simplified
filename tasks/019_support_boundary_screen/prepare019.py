"""Freeze whitelisted 019 requests and protocol before paid execution."""
from collections import Counter
from pathlib import Path
import argparse, csv, difflib, sys
import common019 as c

def prepare(stage):
    require_stage = stage in ('probe','selection','validation')
    c.require(require_stage, 'Unknown stage')
    if stage == 'validation':
        gate = c.read(c.OUT/'selection_freeze.json')
        c.require(gate['passed'], 'Selection gate did not pass')
    folder = c.OUT/stage/'preparation'
    c.require(not folder.exists(), 'Preparation already exists')
    folder.mkdir(parents=True)
    inputs, labels = [], []
    if stage == 'probe':
        cases = [
            ('The temperature was 37 C.','[1] Temperature: 37 C.'),
            ('The temperature was 39 C.','[1] Temperature: 37 C.'),
            ('The patient received drug A.','[1] Blood test: result pending.'),
            ('The procedure was planned.','[1] Plan: procedure tomorrow.'),
            ('Both test A and test B were negative.','[1] Test A negative. Test B positive.'),
            ('The patient was discharged.','[1] Discharged today.')]
        inputs = [dict(proposition_id=f'synthetic_{i}',subject_id='synthetic',author_type='synthetic',
            text=t,reference=r) for i,(t,r) in enumerate(cases)]
    else:
        q = '010' if stage=='selection' else '016'
        order = c.old.baseline.patient_order()
        expected = set(order[18:24] if q=='010' else order[24:30])
        for m in c.jsonlines(c.MATERIALS):
            r = m['row']
            if r['cohort'] != q: continue
            c.require(r['subject_id'] in expected and r['invalid']=='False' and r['proposition_type']=='claim','Unexpected cohort')
            ref = m['references']['C']
            c.require(ref==m['pipeline']['baseline']['reference'],'Reference mismatch')
            inputs.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],text=r['text'],reference=ref))
            labels.append({k:r[k] for k in ('proposition_id','subject_id','author_type','human_gt','C','O','case_id')})
        c.require(len(inputs)==(650 if q=='010' else 601),'Wrong denominator')
        c.require(set(r['subject_id'] for r in inputs)==expected,'Patient mismatch')
    jobs, assignments = {}, []
    for row in sorted(inputs,key=lambda r:c.rank(r['proposition_id'])):
        bundle = []
        for rep in (range(2) if stage=='validation' else range(1)):
            for arm in ('B','S'):
                body = c.body(row['text'],row['reference'],arm=='S')
                rid = f'019:{stage}:r{rep}:'+c.fingerprint(body)
                job = dict(request_id=rid,stage=stage,arm=arm,repeat=rep,proposition_id=row['proposition_id'],body=body)
                jobs.setdefault(rid,job)
                bundle.append(dict(proposition_id=row['proposition_id'],arm=arm,repeat=rep,request_id=rid,body_sha256=c.fingerprint(body)))
        assignments.extend(sorted(bundle,key=lambda x:c.rank(x['request_id'])))
    ordered_jobs = list({a['request_id']:jobs[a['request_id']] for a in assignments}.values())
    c.write_lines(folder/'inputs.jsonl',inputs)
    c.write_lines(folder/'jobs.jsonl',ordered_jobs)
    c.write_csv(folder/'assignments.csv',assignments)
    b = c.body('Synthetic proposition','[1] Synthetic evidence.')
    s = c.body('Synthetic proposition','[1] Synthetic evidence.',True)
    c.write_json(folder/'prompt_and_schema.json',dict(B=b,S=s))
    (folder/'prompt.diff').write_text(''.join(difflib.unified_diff(b['messages'][0]['content'].splitlines(True),s['messages'][0]['content'].splitlines(True),fromfile='B',tofile='S')),encoding='utf-8')
    c.write_json(folder/'summary.json',dict(stage=stage,claims=len(inputs),logical_requests=len(assignments),unique_requests=len(jobs),
        expected_cny=sum((len(c.canonical(j['body']))*0.35*3+500*9)/1e6 for j in jobs.values()),
        patients=sorted({r['subject_id'] for r in inputs}),authors=dict(Counter(r['author_type'] for r in inputs)),
        reference_changes=0,GT_in_requests=False,remaining10_used=False,reserved_test_used=False))
    deps = [c.PROMPTS,c.MATERIALS,c.TASK/'README.md',c.ROOT/'outputs/003_error_analysis/patient_groups.json']
    if stage=='validation': deps.append(c.OUT/'selection_freeze.json')
    paths = list(folder.glob('*'))+deps
    c.write_json(folder/'manifest.json',dict(created_utc=c.now(),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in paths}))
    if labels:
        c.write_csv(c.OUT/stage/'cohort.csv',labels)
        c.write_json(c.OUT/stage/'cohort_manifest.json',dict(sha256={(c.OUT/stage/'cohort.csv').relative_to(c.ROOT).as_posix():c.file_hash(c.OUT/stage/'cohort.csv')}))
    print(c.canonical(c.read(folder/'summary.json')),flush=True)

def authorize():
    c.require(not (c.OUT/'authority.json').exists(),'Already authorized')
    accounts = [a for a in c.load_accounts(c.ROOT/'.env.siliconflow_pool',environ={}) if int(a.alias.split('_')[-1])>=2]
    cfg = c.load_config(c.ROOT/'.env.aliyun')
    c.require(accounts and cfg.api_key, 'Missing local credentials')
    code = list(c.TASK.glob('*.py')) + list((c.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    code += [c.ROOT/'src/verifact_research/inference'/n for n in ('siliconflow_pool.py','aliyun.py')]
    code += [Path(m.__file__) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None) and str(c.ROOT/'tasks') in m.__file__ and m.__file__.endswith('.py')]
    code = list(set(code))
    p = c.read(c.OUT/'selection/preparation/summary.json')
    expected = p['expected_cny'] * (3704/1300) + 8
    c.require(expected<=80,'Conditional whole-task estimate above budget')
    c.write_json(c.OUT/'authority.json',dict(created_utc=c.now(),authorization='User explicitly requested execution of019 through Remote Desktop Commander; latest pool then single Alibaba key; cumulative80 CNY',
        cap_cny=80,expected_whole_task_cny=expected,accounts=[a.alias for a in accounts],SF_model=c.MODEL,Alibaba_model=c.ALI_MODEL,Alibaba_endpoint=cfg.endpoint,
        usage_price_input_output=[3,9],pricing_basis='2026-09-18 official peak no-cache; conservative ignores discounts',
        sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code+[c.TASK/'README.md']},
        price_sources=['https://docs.siliconflow.cn/docs/release-notes/overview','https://help.aliyun.com/zh/model-studio/deepseek-v4-flash']))
    print('AUTHORIZED',round(expected,4),'CNY planned; hard cap80; no keys printed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['probe','selection','validation','authorize']);a=p.parse_args()
    authorize() if a.stage=='authorize' else prepare(a.stage)
