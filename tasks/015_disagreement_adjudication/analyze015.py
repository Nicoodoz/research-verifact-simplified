"""Complete receipt-only 002 comparisons and the preregistered all-or-stop gate."""
from pathlib import Path
import argparse
from collections import Counter
import hashlib
import common015 as c

def load_results():
    c.verify_preparation();c.require(not (c.OUT/'task_api.lock').exists(),'Execution running')
    jobs=c.jsonlines(c.OUT/'preparation_001/jobs.jsonl');state=c.read(c.OUT/'live/state.json');manifest=c.read(c.OUT/'live/manifest.json')
    c.require(c.fingerprint(manifest)==state['run_id'],'Run binding')
    values={};attempts=[];seen=set()
    for j in jobs:
        p=state['jobs'][j['request_id']];success=[]
        for ptr in p['receipts']:
            path=c.OUT/'live'/ptr['file'];seen.add(path.name)
            c.require(c.file_hash(path)==ptr['sha256'],'Receipt changed')
            r=c.read(path);tr=r['transport']
            c.require(r['run_id']==state['run_id'] and r['job_sha256']==c.fingerprint(j) and r['request_id']==j['request_id'],'Receipt binding')
            charge,basis=c.cost(j,tr)
            c.require(abs(charge-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Cost mismatch')
            attempts.append(dict(request_id=j['request_id'],arm=j['arm'],case_id=j['case_id'],attempt=r['attempt'],
                account=r['account'],http_status=tr['http_status'],charge_cny=charge,charge_basis=basis,
                started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],receipt=path.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
            if tr['http_status']==200:success.append(r)
        for u in p.get('unreceipted',[]):
            attempts.append(dict(request_id=j['request_id'],arm=j['arm'],case_id=j['case_id'],attempt=u['attempt'],account=p.get('account'),
                http_status=0,charge_cny=u['reservation'],charge_basis='unreceipted_unknown',started_utc='',ended_utc='',receipt='',sha256=''))
        c.require(len(success)<=1,'Answer regenerated')
        values[j['request_id']]=c.normalize(j,success[0]) if success else dict(status='failed',verdict=None,structural_errors=['No successful receipt'])
    c.require(seen=={p.name for p in (c.OUT/'live').glob('receipt_*.json')},'Unbound receipts')
    c.require(abs(sum(r['charge_cny'] for r in attempts)-state['used_or_reserved_cny'])<1e-8,'Ledger total mismatch')
    c.require(state['used_or_reserved_cny']<=40 and not state.get('bound_violation'),'Budget violation')
    return jobs,values,attempts

def select_cases(rows):
    selected=[]
    for a in ('llm','human'):
        for bucket in ('v4_only_correct','qwen_only_correct','both_wrong_disagreement'):
            for right in (True,False):
                pool=[r for r in rows if r['author_type']==a and r['bucket']==bucket and (r['adjudication']==r['human_gt'])==right]
                chosen=[]
                for _ in range(min(2,len(pool))):
                    row=min([r for r in pool if r not in chosen],key=lambda r:(r['human_gt'] in {x['human_gt'] for x in chosen},
                        r['subject_id'] in {x['subject_id'] for x in chosen},hashlib.sha256(('015/semantic/v1:'+r['proposition_id']).encode()).hexdigest()))
                    chosen.append(row)
                selected+=chosen
    return selected

def analyze(out):
    c.require(not out.exists(),'Analysis output exists')
    jobs,values,attempts=load_results();rows=c.csvrows(c.OUT/'preparation_001/ledger.csv');cohort=c.csvrows(c.OUT/'preparation_001/cohort.csv')
    out.mkdir(parents=True)
    c.write_csv(out/'attempts.csv',attempts)
    c.write_lines(out/'normalized_responses.jsonl',[dict(values[j['request_id']],arm=j['arm'],case_id=j['case_id']) for j in jobs])
    jmap={(j['proposition_id'],j['arm']):j for j in jobs}
    for r in rows:
        for arm in c.ARMS:
            if r['baseline']==r['qwen']:r[arm]=r['baseline']
            else:r[arm]=values[jmap[(r['proposition_id'],arm)]['request_id']]['verdict']
        r['adjudication_matches']=('agreement' if r['baseline']==r['qwen'] else
            'v4' if r['adjudication']==r['baseline'] else 'qwen' if r['adjudication']==r['qwen'] else 'third_label')
        r['candidate_A_source']=c.candidate_order(r['proposition_id'])[0] if r['bucket']!='agreement' else ''
    c.write_csv(out/'transitions.csv',rows)
    failed=[dict(values[j['request_id']],case_id=j['case_id'],arm=j['arm']) for j in jobs if values[j['request_id']]['status']!='success']
    if failed:
        c.write_json(out/'summary.json',dict(status='blocked_missing',failed=failed,task_cost_or_reserved_cny=sum(x['charge_cny'] for x in attempts)))
        c.write_json(out/'gate.json',dict(winner=False,reason='Incomplete required predictions'))
        return
    pred={name:[dict(proposition_id=r['proposition_id'],verdict=r[key]) for r in rows] for name,key in
        [('v4','baseline'),('qwen','qwen'),('adjudication','adjudication'),('evidence_only','evidence_only')]}
    for name,pp in pred.items():c.write_csv(out/('predictions_'+name+'.csv'),pp)
    metrics={};pairs={};core=[];classes=[];patients=[]
    for author in ('llm','human'):
        own=[r for r in cohort if r['author_type']==author];ids={r['proposition_id'] for r in own}
        pp={name:[r for r in p if r['proposition_id'] in ids] for name,p in pred.items()}
        metrics[author]={name:c.evaluate(own,p,iterations=1000,missing='error') for name,p in pp.items()}
        pairs[author]={f'{new}_minus_{old}':c.paired_compare(own,pp[old],pp[new],iterations=1000)
            for new,old in [('adjudication','v4'),('adjudication','qwen'),('adjudication','evidence_only'),('evidence_only','v4'),('evidence_only','qwen')]}
        for name,m in metrics[author].items():
            core.append(dict(author=author,model=name,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),
                pa=m['percent_agreement'],ac1=m['gwet_ac1'],mcc=m['mcc']))
            for label,v in m['per_class'].items():classes.append(dict(author=author,model=name,label=label,**v))
        for sid in sorted({r['subject_id'] for r in own}):
            sub=[r for r in own if r['subject_id']==sid];pids={r['proposition_id'] for r in sub}
            for name,p in pp.items():
                m=c.evaluate(sub,[r for r in p if r['proposition_id'] in pids],profile='none')
                patients.append(dict(subject_id=sid,author=author,model=name,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),
                    pa=m['percent_agreement'],ac1=m['gwet_ac1'],mcc=m['mcc'],mcc_denominator_zero=m['mcc_denominator_zero'],confusion_matrix=c.canonical(m['confusion_matrix'])))
    gate=c.gate(rows,metrics)
    buckets=[];orders=[]
    for author in ('llm','human'):
        own=[r for r in rows if r['author_type']==author]
        for group in ('agreement','v4_only_correct','qwen_only_correct','both_wrong_disagreement'):
            rr=[r for r in own if r['bucket']==group]
            buckets.append(dict(author=author,bucket=group,n=len(rr),**{k+'_correct':c.correct(rr,k) for k in ('baseline','qwen',*c.ARMS)},
                selected_v4=sum(r['adjudication_matches']=='v4' for r in rr),selected_qwen=sum(r['adjudication_matches']=='qwen' for r in rr),third_label=sum(r['adjudication_matches']=='third_label' for r in rr)))
        for source in ('v4','qwen'):
            rr=[r for r in own if r['candidate_A_source']==source]
            orders.append(dict(author=author,candidate_A_source=source,n=len(rr),adjudication_correct=c.correct(rr,'adjudication'),
                picked_A=sum(r['adjudication_matches']==source for r in rr),picked_B=sum(r['adjudication_matches'] in ('v4','qwen') and r['adjudication_matches']!=source for r in rr),
                picked_third=sum(r['adjudication_matches']=='third_label' for r in rr)))
    costs={};usage={}
    for arm in c.ARMS:
        ns=[values[j['request_id']] for j in jobs if j['arm']==arm]
        u=dict(input_tokens=sum(v['usage']['input_tokens'] for v in ns),output_tokens=sum(v['usage']['output_tokens'] for v in ns),
            reasoning_tokens=sum(v['usage']['reasoning_tokens'] for v in ns),adherence_flagged=sum(bool(v['adherence_errors']) for v in ns))
        usage[arm]=u;costs[arm]=dict(actual_usage_or_reservations_cny=sum(a['charge_cny'] for a in attempts if a['arm']==arm),
            uniform_no_cache_no_discount_cny=(u['input_tokens']*3+u['output_tokens']*9)/1e6)
    old=c.read(c.prior.OUT/'analysis_001/summary.json')['usage'];b=old['v4_010'];q=old['qwen']
    bv=(b['input_tokens']*3+b['output_tokens']*9)/1e6;qq=(q['input_tokens']*3+q['output_tokens']*12)/1e6
    full=bv+qq+costs['adjudication']['uniform_no_cache_no_discount_cny']
    economics=dict(v4_650_uniform_cny=bv,qwen_650_uniform_cny=qq,full_pipeline_uniform_cny=full,
        pipeline_over_v4=full/bv,pipeline_over_qwen=full/qq,
        deployed_calls=1300+78,baseline_calls=650,experimental_new_calls=156,
        retrieval_cost_excluded_common_to_all=True,cache_time_discounts_excluded_for_fair_comparison=True,
        historical_failures_excluded_from_ideal_deployment=True)
    selected=select_cases(rows);c.write_csv(out/'selected_cases.csv',selected)
    source={r['proposition_id']:r for r in c.jsonlines(c.OUT/'preparation_001/candidate_sources.jsonl')}
    (out/'cases').mkdir()
    for r in selected:
        s=source[r['proposition_id']];payload=c.pilot.strict_json(s['base_body']['messages'][1]['content'])
        packet=dict(row=r,claim=payload['proposition'],reference=payload['reference'],v4_output=s['v4_output'],qwen_output=s['qwen_output'],
            **{a+'_output':values[jmap[(r['proposition_id'],a)]['request_id']]['output_text'] for a in c.ARMS})
        c.write_json(out/'cases'/(r['case_id']+'.json'),packet)
    summary=dict(status='complete',claims=650,disagreements=78,agreement_passthrough=572,
        valid_new_predictions=len(values),http_attempts=len(attempts),http_status_counts=dict(Counter(a['http_status'] for a in attempts)),
        accounts=dict(Counter(a['account'] for a in attempts)),task_cost_or_reserved_cny=sum(a['charge_cny'] for a in attempts),
        usage=usage,costs=costs,economics=economics,winner=gate['winner'],semantic_cases=len(selected),
        started_utc=min(a['started_utc'] for a in attempts if a['started_utc']),ended_utc=max(a['ended_utc'] for a in attempts if a['ended_utc']),
        independent_audit=False,new_patient_confirmation_started=False)
    for name,value in [('metrics',metrics),('paired',pairs),('gate',gate),('summary',summary)]:c.write_json(out/(name+'.json'),value)
    for name,value in [('core_results',core),('classes',classes),('patients',patients),('bucket_outcomes',buckets),('order_diagnostics',orders)]:c.write_csv(out/(name+'.csv'),value)
    c.write_json(out/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in out.rglob('*') if p.is_file()},
        code_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [Path(__file__),c.TASK/'common015.py']},
        dependencies={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [c.OUT/'preparation_001/manifest.json',c.OUT/'live/state.json']}))
    print(c.canonical(summary));print(c.canonical(gate))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'analysis_001');analyze(p.parse_args().output.resolve())
