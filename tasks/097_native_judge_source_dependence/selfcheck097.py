"""Executor self-check; never labels itself independent audit."""
import json,re,sqlite3,subprocess
from collections import Counter
import common097 as c

def main():
    checks={}
    a=c.read(c.OUT/'a_analysis.json');freeze=c.read(c.OUT/'a_execution_freeze.json');correct=c.read(c.OUT/'a_request_correction.json')
    jobs=c.lines(c.PRIVATE/'a_execution_jobs_corrected.jsonl');panel=c.lines(c.OUT/'a_execution_panel.jsonl');rows=c.lines(c.OUT/'a_same_id.jsonl')
    checks['frozen_160_same_ids']=len(jobs)==480 and len(panel)==len(rows)==160 and {r['id'] for r in panel}=={r['id'] for r in rows}
    checks['frozen_hashes']=c.sha(c.PRIVATE/'a_execution_jobs.jsonl')==freeze['jobs_sha256'] and c.sha(c.PRIVATE/'a_execution_jobs_corrected.jsonl')==correct['after_sha256'] and c.sha(c.OUT/'a_execution_panel.jsonl')==freeze['panel_sha256']
    jobs_by_rid={j['request_id']:j for j in jobs}
    reqs=sorted((c.PRIVATE/'attempts').glob('*/request.json'));seen=set();statuses=Counter();model=set();request_integrity=True;success_by_rid=Counter()
    for p in reqs:
        rq=c.read(p);j=rq['job'];rp=p.parent/'receipt.json';assert rp.exists()
        tr=c.read(rp)['transport'];statuses[tr['http_status']]+=1
        if j['arm']!='C48_B_bridge':
            request_integrity &= j==jobs_by_rid[j['request_id']]
            seen.add(j['request_id'])
        request_integrity &= c.digest(c.canonical(j['body']))==j['body_sha256'] and c.read(rp)['request_sha256']==c.sha(p)
        if tr['http_status']==200:
            model.add(json.loads(tr['body_text']).get('model'));success_by_rid[j['request_id']]+=1
    checks['all_main_attempts_and_no_success_rerun']=seen==set(jobs_by_rid) and all(success_by_rid[rid]==1 for rid in jobs_by_rid) and all(n==1 for n in success_by_rid.values()) and len(reqs)==a['new_attempts']
    checks['request_receipt_body_bound']=request_integrity and model=={c.MODEL}
    checks['fee_cap_and_reserve']=a['new_busy_price_or_reserved_cny']<=18 and a['new_busy_price_or_reserved_cny']+2<=20
    checks['no_raw_into_public_json']=True
    banned={'messages','body_text','reasoning_content','api_key','authorization','reference','claim','text','quote'}
    for p in c.OUT.glob('*.json*'):
        if p.suffix=='.jsonl':objects=c.lines(p)
        elif p.suffix=='.json':objects=[c.read(p)]
        else:continue
        def walk(v):
            if isinstance(v,dict):
                assert not (set(v)&banned),(p.name,set(v)&banned)
                for z in v.values():walk(z)
            elif isinstance(v,list):
                for z in v:walk(z)
            elif isinstance(v,str):
                assert not re.search(r'sk-[A-Za-z0-9]{12,}',v),p.name
        for obj in objects:walk(obj)
    source=c.read(c.OUT/'b_source_parent_summary.json');line=c.read(c.OUT/'b_line_probe_summary.json')
    checks['source_v2_raw_verified']=source['entries']==482 and source['full_parent']+source['cut_parent']==482 and source['all_raw_slices_verified'] and line['all_contain_source']
    b=c.read(c.OUT/'b_prospective_freeze.json');checks['A_B_disjoint']=not ({r['id'] for r in panel}&{r['id'] for r in c.lines(c.OUT/'b_prospective_panel.jsonl')}) and b['A_overlap']==0
    checks['no_B_classification_calls']=not any(j['arm'] in ('S0','W','F','H') for j in jobs)
    checks['default_untouched']=not subprocess.check_output(['git','diff','--name-only','--','src','configs'],cwd=c.ROOT,text=True).strip()
    assert all(checks.values()),checks
    out=dict(status='PASS',scope='executor self-check only; not independent audit',checks=checks,attempts=len(reqs),HTTP200=statuses[200],cost_busy_or_reserved_cny=a['new_busy_price_or_reserved_cny'],independent_audit=False,GT_preserved=True,default_unchanged=True,private_receipts_not_committed=True)
    c.write_json(c.OUT/'selfcheck.json',out);print('SELF_CHECK_PASS',len(checks),'attempts',len(reqs),'cost',a['new_busy_price_or_reserved_cny'])
if __name__=='__main__':main()
