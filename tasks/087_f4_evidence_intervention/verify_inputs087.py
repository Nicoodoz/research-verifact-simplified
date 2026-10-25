from collections import Counter
from common087 import *
import run087 as r

def main():
    jobs=r.check_jobs();samples=lines(OUT/'sample_blind.jsonl');t=read(OUT/'templates.json');coverage=read(OUT/'coverage.json')
    checks=0
    def ok(v):
        nonlocal checks
        assert v;checks+=1
    ok(len(samples)==len({x['id'] for x in samples})==110)
    ok(Counter(x['sid'] for x in samples)==Counter({sid:5 for sid in coverage['eval_patients']}))
    ok(not set(coverage['eval_patients'])&(set(coverage['prior_source_patients'])|set(coverage['actual_demo_patients'])))
    byid={x['id']:x for x in samples}
    broad={x['proposition_id']:x for x in lines(ROOT/'outputs/032_evidence_relation_correction/preparation_001/inputs_blind.jsonl')}
    for x in samples:
        z=broad[x['id']]
        ok((x['claim'],x['reference'],x['sid'],x['fallback_U2'])==(z['text'],z['reference'],z['subject_id'],LABELS[z['u2']]))
        ok('GT' not in x and 'scores' not in x)
        for a in ('B','F4'):
            for rel in x['prior_exact_requests'][a]:
                q=read(ROOT/rel);body=q.get('body') or q.get('job',{}).get('body')
                ok(h(canonical(body))==next(j['body_sha256'] for j in jobs if j['id']==x['id'] and j['arm']==a))
    for j in jobs:
        x=byid[j['id']];b=j['body'];target=json.loads(b['messages'][1]['content'])
        ok(target==dict(proposition=x['claim'],reference=x['reference']))
        ok(b['messages'][0]['content']==t['systems'][j['arm']])
        peers=[z for z in jobs if z['id']==j['id']]
        ok({z['arm'] for z in peers}==set(ARMS))
        ok(all({k:v for k,v in z['body'].items() if k!='messages'}=={k:v for k,v in b.items() if k!='messages'} for z in peers))
    ex=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl')
    for a in ARMS:ok(render(t['systems']['B'],t['header'],ex,a)==t['systems'][a])
    ok(read(OUT/'budget.json')['length_retry_unknown_buffer']>=3)
    put(OUT/'input_selfcheck.json',dict(status='PASS',checks=checks,new_api_calls=0,independent_audit=False))
    print(canonical(dict(checks=checks,status='PASS',tiers=coverage['chosen_tier_counts'],
        teaching_patient_overlap=sum(x['teaching_candidate_patient_overlap'] for x in samples),
        prior_target_exposure=sum(bool(x['prior_target_exposure']) for x in samples))))

if __name__=='__main__':main()
