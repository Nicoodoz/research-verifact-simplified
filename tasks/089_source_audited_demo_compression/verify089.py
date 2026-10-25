"""Offline executor self-check, not an independent audit or medical review."""
from collections import Counter
import subprocess
from common089 import *
import api089 as api
from analyze089 import parse_arm,metric,PAIRS
from construct089 import source_check,render_reference

def main():
    count=0
    def check(ok,why):
        nonlocal count
        assert ok,why;count+=1
    for freeze in ('constructor_freeze.json','main_freeze.json','preflight.json'):
        f=read(OUT/freeze)
        for rel,d in f.get('sources',{}).items():check(sha(ROOT/rel)==d,rel)
        for rel,d in f.get('files',{}).items():check(sha(OUT/rel)==d,rel)
    for rel,d in read(OUT/'demonstration_freeze.json')['files'].items():check(sha(OUT/rel)==d,rel)
    examples=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');arms=read(OUT/'demonstrations.json');units=read(OUT/'source_units.json');records=read(OUT/'construction_summary.json')
    for a in ARMS:
        for i,(old,new) in enumerate(zip(examples,arms[a])):
            check({k:v for k,v in old.items() if k!='reference'}=={k:v for k,v in new.items() if k!='reference'},'demo identity changed')
            ids=[x['id'] for x in units[old['proposition_id']]['units']] if a=='F4' else records[i][a]['selected_ids']
            check(source_check(old['reference'],units[old['proposition_id']],ids,new['reference']),'provenance')
    systems=read(OUT/'templates.json')['systems'];check(systems['F4']==read(ROOT/'outputs/087_f4_evidence_intervention/templates.json')['systems']['F4'],'original F4')
    jobs=api.validate_main();aliases=lines(OUT/'logical_aliases.jsonl');attempts,success,counts=api.state()
    check(all(j['request_id'] in success for j in jobs),'main incomplete');check(all(c<=3 for c in counts.values()),'retry cap')
    main_ids={j['request_id'] for j in jobs};check(len(main_ids)==len(jobs),'duplicate physical job')
    sample=lines(OUT/'sample_blind.jsonl');sm={x['id']:x for x in sample};check(len(sm)==len(sample),'panel overlap')
    pred=lines(OUT/'predictions.jsonl');pm={x['id']:x for x in pred};check(set(pm)==set(sm),'prediction coverage')
    check(Counter(x['sid'] for x in sample if x['panel']=='natural')==Counter({s:5 for s in read(OUT/'sampling_audit.json')['eval_patients']}),'natural equal count')
    pressure=[x for x in pred if x['panel']=='pressure'];check(Counter(x['GT'] for x in pressure)==Counter({'Not Supported':22,'Not Addressed':22}),'pressure labels')
    check(max(Counter((x['sid'],x['GT']) for x in pressure).values())<=3,'pressure concentration')
    jf={j['request_id']:j for j in jobs}
    for j in jobs:
        x=sm[j['id']];check(j['body']['messages'][0]['content']==systems[j['arm']],'system drift')
        check(json.loads(j['body']['messages'][1]['content'])==dict(proposition=x['claim'],reference=x['reference']),'target/label contamination')
        check(h(canonical(j['body']))==j['body_sha256'],'body fingerprint')
    for al in aliases:
        j=jf[al['request_id']];check(al['body_sha256']==j['body_sha256'],'alias hash')
        check(systems[al['arm']]==j['body']['messages'][0]['content'],'nonidentical sharing')
        s=success[al['request_id']];info,labels=parse_arm(read(ROOT/s['receipt_source'])['transport'],sm[al['id']]['fallback_U2'])
        x=pm[al['id']];check(labels==x['labels'][al['arm']],'reparse labels')
        check(info['raw_verdict']==x['arms'][al['arm']]['raw_verdict'],'raw preserved')
    for jpath in (OUT/'registered_jobs').glob('*.json'):
        j=read(jpath)
        if j['phase'].endswith('review'):
            payload=json.loads(j['body']['messages'][1]['content'])
            check(set(payload)=={'claim','original_reference','source_units','selected_ids','candidate_reference'},'review blindness')
        if j['phase'].startswith('fixed_'):
            check(j['id'] in {x['proposition_id'] for x in examples},'target enters construction')
    fixed=[read(p) for p in (OUT/'registered_jobs').glob('*.json') if read(p)['phase'].startswith('fixed_')]
    check(Counter((j['phase'],j['arm']) for j in fixed)==Counter({(p,a):2 for p in ('fixed_construct','fixed_review') for a in ('P4','Q4')}),'independent equal calls')
    analysis=read(OUT/'analysis.json')
    for panel in ('natural','pressure'):
        z=[x for x in pred if x['panel']==panel]
        for m in METHODS:
            for a in ('Original',)+ARMS:
                direct=metric(z,a,m,False);stored=analysis['panels'][panel]['full_metrics'][m][a]
                for k in ('n','correct','MCC','PA','Macro_F1','false_S','confusion_matrix','per_class'):check(direct[k]==stored[k],f'metric {panel}/{a}/{m}/{k}')
        for m in METHODS:
            for b,c in PAIRS:
                x=analysis['panels'][panel]['full_comparisons'][m][f'{c}-{b}']
                check(x['net']==sum(y['labels'][c][m]==y['GT'] for y in z)-sum(y['labels'][b][m]==y['GT'] for y in z),'net count')
    costs=read(OUT/'cost_ledger.json');check(abs(sum(x['cost_or_unknown_cny'] for x in attempts)-costs['total_original_or_unknown_cny'])<1e-9,'task ledger')
    check(costs['total_original_or_unknown_cny']<=20 and costs['construction_review_coverage_cny']<=2,'budget')
    check((ROOT/'outputs/087_f4_evidence_intervention/086_correction.md').exists(),'086 correction')
    check(subprocess.check_output(['git','diff','HEAD','--','.gitignore'],cwd=ROOT)==b'','gitignore changed')
    check(not (OUT/'run.lock').exists(),'runner active')
    result=dict(status='PASS',checks=count,synthetic_tests=11,independent_audit=False,created_utc=now(),predictions_sha256=sha(OUT/'predictions.jsonl'),analysis_sha256=sha(OUT/'analysis.json'))
    if (OUT/'selfcheck.json').exists():
        old=read(OUT/'selfcheck.json')
        for k in ('status','checks','synthetic_tests','independent_audit','predictions_sha256','analysis_sha256'):check(old[k]==result[k],'selfcheck replay drift')
        print(canonical(dict(status='PASS',replay_checks=count,network_calls=0)))
    else:put(OUT/'selfcheck.json',result);print(canonical(result))
if __name__=='__main__':main()
