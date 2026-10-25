"""Receipt-only complete-cohort evaluation; no API and no method selection."""
from pathlib import Path
from collections import Counter
import argparse
import duckdb
import pandas as pd
import common016 as c
from io016 import load_phase
from decisions016 import compose,first_gate,correct

METHODS=('v4_first','qwen','cross_repeat','cross_review','released')

def released(cohort):
    master=c.ROOT/'outputs/002_reproduce_paper_results/run_003';formal=c.read(master/'manifest.json')
    files=[c.RAW/'verifact'/n for n in ('verdicts.parquet','rater_configurations.csv')]
    for p in files:c.require(c.file_hash(p)==formal['input_sha256'][p.relative_to(c.RAW).as_posix()],'Release changed')
    expected=dict(model='R1-70B',fact_type='sentence',top_n='100',retrieval_method='rerank',reference_format='absolute_time',reference_only_admission='True',deduplicate_text='True')
    configs=[r for r in c.csvrows(files[1]) if all(r[k]==v for k,v in expected.items())]
    c.require(len(configs)==1 and configs[0]['rater_alias']=='v1.1.0-rater-121','Release config')
    ids={r['proposition_id'] for r in cohort}
    with duckdb.connect() as db:
        db.register('selected',pd.DataFrame({'proposition_id':sorted(ids)}))
        values=db.execute('SELECT v.proposition_id,v.verdict FROM read_parquet(?) v JOIN selected USING(proposition_id) WHERE v.rater_alias=?',[str(files[0]),configs[0]['rater_alias']]).fetchall()
    c.require(len(values)==len(dict(values))==601,'Release incomplete')
    exports=[master/'baseline_predictions'/f'R1-70B_{a}_claim_valid_only.csv' for a in ('llm','human')]
    exported={r['proposition_id']:r['verdict'] for p in exports for r in c.csvrows(p) if r['proposition_id'] in ids}
    c.require(dict(values)==exported,'002 released prediction mismatch')
    return dict(values),dict(configuration=configs[0],sources_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in files+exports},reference_payload_not_read=True)

def analyze(out):
    c.require(not out.exists(),'Analysis already exists');root=c.OUT/'stage1';prep=root/'preparation_002';base=root/'base_preparation_001';review=root/'review_preparation_001'
    for p in (prep,base,review):c.check_manifest(p)
    cohort=c.csvrows(prep/'cohort.csv');inputs={r['proposition_id']:r for r in c.jsonlines(base/'inputs.jsonl')}
    rel,relmeta=released(cohort);norm={};attempts=[];values={};role_by_pid={};normal=[]
    ledger=c.read(c.OUT/'live/ledger.json')
    for phase in ledger['phases']:
        vv,aa=load_phase(phase);values.update(vv);attempts+=aa
        for rid,v in vv.items():
            if v['job']['kind']!='chat':continue
            n=c.normalize(v['job'],v['receipt']) if v['receipt'] else dict(request_id=rid,status='failed',verdict=None,structural_errors=['No successful response'])
            norm[rid]=n;normal.append(dict(n,role=v['job']['role']))
    assignments=c.csvrows(base/'assignments.csv')+c.csvrows(review/'assignments.csv')
    for a in assignments:
        key=(a['proposition_id'],a['role']);c.require(key not in role_by_pid,'Duplicate assignment');role_by_pid[key]=a['request_id']
        c.require(a['body_sha256']==c.fingerprint(values[a['request_id']]['job']['body']),'Body assignment mismatch')
    out.mkdir(parents=True);c.write_csv(out/'attempts.csv',attempts);c.write_lines(out/'normalized_responses.jsonl',normal);c.write_json(out/'release_binding.json',relmeta)
    failed=[n for n in normal if n['status']!='success']
    if failed:
        c.write_json(out/'summary.json',dict(status='incomplete_stop',failed=failed,task_used_or_reserved_cny=ledger['used_or_reserved_cny']))
        c.write_json(out/'gate.json',dict(passed=False,reason='Incomplete predictions; no available-case method claim'));return
    rows=[]
    for r in cohort:
        pid=r['proposition_id'];item=inputs[pid]
        row={k:r[k] for k in ('proposition_id','subject_id','author_type','human_gt')};row['case_id']=item['case_id'];row['released']=rel[pid]
        for role in c.ROLES:row[role]=norm[role_by_pid[(pid,role)]]['verdict'] if (pid,role) in role_by_pid else ''
        rows.append(row)
    rows=compose(rows);dis={r['proposition_id'] for r in rows if r['cross_trigger']}
    c.require({pid for pid,role in role_by_pid if role=='v4_repeat'}==dis=={pid for pid,role in role_by_pid if role=='independent_review'},'Disagreement-only coverage violated')
    for r in rows:
        b=r['v4_first']==r['human_gt'];q=r['qwen']==r['human_gt']
        r['bucket']='agreement_correct' if not r['cross_trigger'] and b else 'agreement_wrong' if not r['cross_trigger'] else 'v4_only_correct' if b else 'qwen_only_correct' if q else 'both_wrong_disagreement'
        r['review_choice']='agreement' if not r['cross_trigger'] else 'v4' if r['cross_review']==r['v4_first'] else 'qwen' if r['cross_review']==r['qwen'] else 'third_label'
    pred={name:[dict(proposition_id=r['proposition_id'],verdict=r[name]) for r in rows] for name in METHODS}
    for name,p in pred.items():c.write_csv(out/f'predictions_{name}.csv',p)
    c.write_csv(out/'transitions.csv',rows)
    metrics={};pairs={};core=[];classes=[];patients=[];buckets=[];changes=[];oracle={}
    comparisons=[('cross_review',k) for k in ('v4_first','qwen','cross_repeat','released')]+[('cross_repeat','v4_first'),('cross_repeat','qwen'),('qwen','v4_first')]
    for author in ('llm','human'):
        own=[r for r in cohort if r['author_type']==author];rr=[r for r in rows if r['author_type']==author];ids={r['proposition_id'] for r in own}
        pp={name:[p for p in pred[name] if p['proposition_id'] in ids] for name in METHODS}
        metrics[author]={name:c.evaluate(own,p,iterations=1000,missing='error') for name,p in pp.items()}
        pairs[author]={new+'_minus_'+old:c.paired_compare(own,pp[old],pp[new],iterations=1000) for new,old in comparisons}
        for name,m in metrics[author].items():
            core.append(dict(author=author,method=name,n=m['n'],correct=correct(rr,name),pa=m['percent_agreement'],ac1=m['gwet_ac1'],mcc=m['mcc']))
            for label,v in m['per_class'].items():classes.append(dict(author=author,method=name,label=label,**v))
        for sid in sorted({r['subject_id'] for r in own}):
            sub=[r for r in own if r['subject_id']==sid];pids={r['proposition_id'] for r in sub}
            for name,p in pp.items():
                m=c.evaluate(sub,[r for r in p if r['proposition_id'] in pids],profile='none')
                patients.append(dict(subject_id=sid,author=author,method=name,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),pa=m['percent_agreement'],ac1=m['gwet_ac1'],mcc=m['mcc'],mcc_denominator_zero=m['mcc_denominator_zero'],confusion_matrix=c.canonical(m['confusion_matrix'])))
        for bucket in ('agreement_correct','agreement_wrong','v4_only_correct','qwen_only_correct','both_wrong_disagreement'):
            sub=[r for r in rr if r['bucket']==bucket]
            buckets.append(dict(author=author,bucket=bucket,n=len(sub),**{k+'_correct':correct(sub,k) for k in METHODS},**{k+'_selected':sum(r['review_choice']==k for r in sub) for k in ('v4','qwen','third_label')}))
        for new,old in comparisons:
            changes.append(dict(author=author,candidate=new,baseline=old,fixed=sum(r[new]==r['human_gt'] and r[old]!=r['human_gt'] for r in rr),broken=sum(r[new]!=r['human_gt'] and r[old]==r['human_gt'] for r in rr),both_wrong_changed=sum(r[new]!=r[old] and r[new]!=r['human_gt'] and r[old]!=r['human_gt'] for r in rr),net=correct(rr,new)-correct(rr,old)))
        agree_correct=sum(not r['cross_trigger'] and r['v4_first']==r['human_gt'] for r in rr);dn=sum(r['cross_trigger'] for r in rr)
        oracle[author]=dict(disagreements=dn,agreement_correct=agree_correct,agreement_wrong=len(rr)-dn-agree_correct,
            perfect_free_review_correct=agree_correct+dn,perfect_candidate_selection_correct=sum(r['v4_first']==r['human_gt'] or r['qwen']==r['human_gt'] for r in rr))
    gate=first_gate(rows,metrics);usage={};costs={}
    for role in c.ROLES:
        nn=[n for n in normal if n['role']==role];u={k:sum(n['usage'][k] for n in nn) for k in ('input_tokens','output_tokens','reasoning_tokens')};u['calls']=len(nn);u['adherence_flagged']=sum(bool(n.get('adherence_errors')) for n in nn);usage[role]=u
        costs[role]=dict(usage_or_reservations_cny=sum(a['charge_cny'] for a in attempts if a['role']==role),peak_no_cache_cny=(u['input_tokens']*3+u['output_tokens']*(12 if role=='qwen' else 9))/1e6)
    bv=costs['v4_first']['peak_no_cache_cny'];qv=costs['qwen']['peak_no_cache_cny'];rv=costs['independent_review']['peak_no_cache_cny']
    economics=dict(ideal_judge_pipeline_peak_no_cache_cny=bv+qv+rv,over_V4=(bv+qv+rv)/bv,over_Qwen=(bv+qv+rv)/qv,
        deployed_logical_judge_calls=1202+len(dis),single_model_logical_calls=601,shared_retrieval_cny=sum(a['charge_cny'] for a in attempts if not a['role']),
        repeat_control_cost_not_in_deployment=True,cache_time_discounts_excluded_for_comparison=True)
    # Deterministic, bounded semantic packets: 2 examples per author / outcome bucket.
    selected=[]
    for a in ('llm','human'):
        for bucket in ('review_gain','review_harm','review_over_repeat','both_wrong'):
            def eligible(r):
                return r['author_type']==a and r['cross_trigger'] and (
                    (r['cross_review']==r['human_gt'] and r['v4_first']!=r['human_gt']) if bucket=='review_gain' else
                    (r['cross_review']!=r['human_gt'] and r['v4_first']==r['human_gt']) if bucket=='review_harm' else
                    (r['cross_review']==r['human_gt'] and r['cross_repeat']!=r['human_gt']) if bucket=='review_over_repeat' else r['bucket']=='both_wrong_disagreement')
            chosen=sorted([r for r in rows if r['author_type']==a and r['cross_trigger'] and eligible(r)],key=lambda r:c.hash_rank(r['proposition_id'],'016/semantic/v1:'))[:2]
            selected.extend(dict(r,selection_bucket=bucket) for r in chosen)
    (out/'cases').mkdir();c.write_csv(out/'selected_cases.csv',selected,list(rows[0])+['selection_bucket'])
    for pid in sorted({r['proposition_id'] for r in selected}):
        r=next(r for r in rows if r['proposition_id']==pid);i=inputs[pid]
        c.write_json(out/'cases'/f'{r["case_id"]}.json',dict(row=r,claim=i['text'],reference=i['reference'],outputs={role:norm[role_by_pid[(pid,role)]]['output_text'] for role in c.ROLES}))
    summary=dict(status='complete',claims=601,authors=dict(Counter(r['author_type'] for r in rows)),patients=c.patient_ids('stage1'),
        disagreements=len(dis),agreement_passthrough=601-len(dis),correct={k:correct(rows,k) for k in METHODS},
        http_attempts=len(attempts),http_status_counts=dict(Counter(a['http_status'] for a in attempts)),accounts=dict(Counter(a['account'] for a in attempts)),
        task_used_or_reserved_cny=ledger['used_or_reserved_cny'],
        received_usage_estimated_cny=sum(a['charge_cny'] for a in attempts if 'unknown' not in a['charge_basis']),
        unknown_or_failed_usage_reservation_cny=sum(a['charge_cny'] for a in attempts if 'unknown' in a['charge_basis']),
        cap_cny=40,usage=usage,costs=costs,economics=economics,oracle=oracle,
        passed=gate['passed'],conclusion='worth_second_stage_only' if gate['passed'] else 'stop_direction',
        started_utc=min(a['started_utc'] for a in attempts if a['started_utc']),ended_utc=max(a['ended_utc'] for a in attempts if a['ended_utc']),
        final_confirmation_performed=False,remaining_development_used=False,reserved_test_used=False,independent_audit=False)
    for name,value in [('metrics',metrics),('paired',pairs),('gate',gate),('summary',summary)]:c.write_json(out/(name+'.json'),value)
    for name,value in [('core_results',core),('classes',classes),('patients',patients),('bucket_outcomes',buckets),('changes',changes)]:c.write_csv(out/(name+'.csv'),value)
    c.seal(out,[prep/'manifest.json',base/'manifest.json',review/'manifest.json',c.OUT/'live/ledger.json'],[Path(__file__),c.TASK/'decisions016.py',c.TASK/'io016.py',c.TASK/'common016.py'])
    print(c.canonical(summary));print(c.canonical(gate))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'analysis_001');analyze(p.parse_args().output.resolve())
