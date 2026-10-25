"""Prepare the requested F4 completion; no network, credentials, or old-file writes."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'outputs/078_component_ablation'
OUT = OLD / 'f4_extension_001'

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def lines(p):
    return [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]

def canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def digest(x):
    return hashlib.sha256(canon(x).encode()).hexdigest()

def main():
    rows = lines(OLD / 'predictions.jsonl')
    examples = read(ROOT / 'outputs/071_judge_icl_feasibility/freeze.json')['examples']
    example_patients = {e['sid'] for e in examples}
    example_ids = {e['proposition_id'] for e in examples}
    existing = [r for r in rows if 'F4' in r['arms']]
    template = read(ROOT / existing[0]['arms']['F4']['request_source'])['job']['body']
    jobs, sources = [], {}
    for r in rows:
        path = ROOT / r['arms']['TS']['request_source']
        sources[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        body = copy.deepcopy(read(path)['job']['body'])
        body['messages'][0]['content'] = template['messages'][0]['content']
        if 'F4' in r['arms']:
            prior = read(ROOT / r['arms']['F4']['request_source'])['job']['body']
            assert canon(body) == canon(prior)
            continue
        jobs.append(dict(request_id='078_F4ext_' + digest(r['id'])[:24], id=r['id'],
                         sid=r['sid'], arm='F4', stage='main', scored=True, thinking=True,
                         body=body, body_sha256=digest(body)))
    assert len(rows) == 384 and len(existing) == 128 and len(jobs) == 256
    jobs.sort(key=lambda j: digest('078/F4extension/v1:' + j['id']))
    cohorts = {
        'all384_descriptive': [r['id'] for r in rows],
        'exclude_actual_example_patients352': [r['id'] for r in rows if r['sid'] not in example_patients],
        'original_pool_isolated128': [r['id'] for r in existing],
        'new256': [j['id'] for j in jobs],
        'same_example_patients32': [r['id'] for r in rows if r['sid'] in example_patients],
        'exact_example_overlap2': [r['id'] for r in rows if r['id'] in example_ids],
    }
    assert [len(cohorts[k]) for k in cohorts] == [384,352,128,256,32,2]
    ledger = read(OLD / 'cost_ledger.json')
    estimated_new = ledger['by_arm']['F4']['cost_cny'] / 80 * 256
    plan = dict(status='PREPARED_NOT_EXECUTED_AWAITING_BUDGET_INCREASE',
                authorization='User requested completing existing F4 to 384 if feasible; no explicit increase to original 30 CNY cap.',
                old_cap_cny=30, old_spent_cny=ledger['estimated_usage_and_unknown_cny'],
                estimated_new_cny=estimated_new,
                estimated_cumulative_cny=ledger['estimated_usage_and_unknown_cny']+estimated_new,
                proposed_cumulative_cap_cny=35, proposed_cap_authorized=False,
                model=template['model'], new_requests=len(jobs), existing_reused=len(existing),
                example_patients=sorted(example_patients), cohorts=cohorts,
                scope='Fixed original F4 and frozen postprocessing; no refit, no baseline repeats. All384 descriptive;352 excludes actual demo patients but not entire candidate pool;128 retains original pool isolation.',
                analysis='Same-ID Original/U2/Gate/StdM/StdV/B/F4 tables; raw/U2/PriorG and common-valid sensitivity; patient bootstrap; subgroup disclosure.',
                source_sha256=sources)
    OUT.mkdir(exist_ok=False)
    with (OUT/'main_jobs.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for j in jobs:
            f.write(canon(j)+'\n')
    plan['jobs_sha256'] = hashlib.sha256((OUT/'main_jobs.jsonl').read_bytes()).hexdigest()
    with (OUT/'proposed_plan.json').open('x',encoding='utf-8',newline='\n') as f:
        json.dump(plan,f,ensure_ascii=False,indent=2)
        f.write('\n')
    print(canon({k:v for k,v in plan.items() if k not in ['cohorts','source_sha256']}))

if __name__ == '__main__':
    main()
