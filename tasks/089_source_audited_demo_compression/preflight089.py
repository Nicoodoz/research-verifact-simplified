"""Final cost reconciliation and offline checks before first main response."""
from common089 import *
import api089 as api
from analyze089 import native_fields
def main():
    assert (OUT/'coverage_summary.json').exists(),'wait for construction coverage completion'
    assert not (OUT/'run.lock').exists()
    jobs=api.validate_main();rows,success,_=api.state();assert not any(x['phase']=='main' for x in rows)
    old=read(OUT/'budget.json');actual=sum(x['cost_or_unknown_cny'] for x in rows);assert actual<=2
    total=old['selected_total_forecast']-old['construction_used']+actual;assert total<=17
    sample=lines(OUT/'sample_blind.jsonl');assert len(sample)==len({x['id'] for x in sample})
    assert sum(x['panel']=='natural' for x in sample)==110
    sm={x['id']:x for x in sample};systems=read(OUT/'templates.json')['systems']
    for j in jobs:
        x=sm[j['id']];assert json.loads(j['body']['messages'][1]['content'])==dict(proposition=x['claim'],reference=x['reference'])
        assert j['body']['messages'][0]['content']==systems[j['arm']]
        assert j['body']['model']==MODEL and j['body']['max_tokens']==8192
    put(OUT/'preflight.json',dict(created_utc=now(),construction_complete_cny=actual,reconciled_total_forecast=total,reserve=20-total,
        main_jobs=len(jobs),natural_n=110,pressure_n=sum(x['panel']=='pressure' for x in sample),
        note='Panel freeze occurred during optional coverage execution; this pre-main reconciliation includes all completed coverage. No IDs, arms, requests or scale changed.',
        sources={p.relative_to(ROOT).as_posix():sha(p) for p in (TASK/'analyze089.py',TASK/'test089.py',TASK/'coverage089.py',TASK/'preflight089.py')},
        budget_sha256=sha(OUT/'budget.json'),main_freeze_sha256=sha(OUT/'main_freeze.json'),coverage_sha256=sha(OUT/'coverage_summary.json')))
    print(canonical(read(OUT/'preflight.json')))
if __name__=='__main__':main()
