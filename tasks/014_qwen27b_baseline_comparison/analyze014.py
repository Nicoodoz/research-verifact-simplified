"""Receipt-only 002 evaluation, complete cohort diagnostics and fixed semantic sampling."""
from collections import Counter
import argparse
import hashlib
from pathlib import Path
import statistics
import common014 as c

def movement(b,q,gt):
    if q is None:return 'missing'
    if b==gt and q==gt:return 'both_correct'
    if q==gt:return 'qwen_corrected'
    if b==gt:return 'qwen_broke'
    return 'both_wrong'

def select_cases(rows):
    selected=[]
    for author in ('llm','human'):
        for group in ('qwen_corrected','qwen_broke','both_wrong','both_correct'):
            pool=[r for r in rows if r['author_type']==author and r['movement']==group]
            chosen=[]
            for _ in range(min(3,len(pool))):
                def priority(r):
                    return (r['human_gt'] in {x['human_gt'] for x in chosen},
                            r['subject_id'] in {x['subject_id'] for x in chosen},
                            (r['baseline']==r['qwen']) in {x['baseline']==x['qwen'] for x in chosen} if group=='both_wrong' else False,
                            hashlib.sha256(('014/case/v1:'+r['proposition_id']).encode()).hexdigest())
                row=min([r for r in pool if r not in chosen],key=priority);chosen.append(row)
            selected+=chosen
    return selected

def load_results():
    c.verify_preparation()
    c.require(not (c.OUT/'task_api.lock').exists(),'Wait for execution to stop')
    jobs=c.jsonlines(c.OUT/'preparation_001/jobs.jsonl')
    state=c.read(c.OUT/'live/state.json');manifest=c.read(c.OUT/'live/manifest.json')
    c.require(c.fingerprint(manifest)==state['run_id'],'Run identity mismatch')
    values={};attempts=[];seen=set()
    for j in jobs:
        p=state['jobs'][j['request_id']];answers=[]
        for ptr in p['receipts']:
            path=c.OUT/'live'/ptr['file'];seen.add(path.name)
            c.require(c.file_hash(path)==ptr['sha256'],'Receipt hash mismatch')
            r=c.read(path)
            c.require(r['run_id']==state['run_id'] and r['request_id']==j['request_id'] and r['job_sha256']==c.fingerprint(j),'Receipt/job mismatch')
            charge,basis=c.cost(j,r['transport'])
            c.require(abs(charge-ptr['charge_cny'])<1e-10 and basis==ptr['charge_basis'],'Cost mismatch')
            tr=r['transport']
            attempts.append(dict(request_id=j['request_id'],case_id=j['case_id'],attempt=r['attempt'],account=r['account'],
                http_status=tr['http_status'],charge_cny=charge,charge_basis=basis,started_utc=tr['started_utc'],ended_utc=tr['ended_utc'],
                receipt=path.relative_to(c.ROOT).as_posix(),sha256=ptr['sha256']))
            if tr['http_status']==200:answers.append(r)
        for u in p.get('unreceipted',[]):
            attempts.append(dict(request_id=j['request_id'],case_id=j['case_id'],attempt=u['attempt'],account=p.get('account'),
                http_status=0,charge_cny=u['reservation'],charge_basis='unreceipted_unknown',started_utc='',ended_utc='',receipt='',sha256=''))
        c.require(len(answers)<=1,'Answer regenerated')
        if answers:values[j['proposition_id']]=c.normalize(j,answers[0])
        else:values[j['proposition_id']]=dict(status='failed',verdict=None,structural_errors=['Missing successful response'])
    c.require(seen=={p.name for p in (c.OUT/'live').glob('receipt_*.json')},'Unexpected receipt files')
    c.require(abs(sum(x['charge_cny'] for x in attempts)-state['used_or_reserved_cny'])<1e-8,'Task cost mismatch')
    return values,attempts

def analyze(output):
    c.require(not output.exists(),'Output exists')
    values,attempts=load_results()
    cohort=c.csvrows(c.OUT/'preparation_001/cohort.csv')
    records=c.jsonlines(c.OUT/'preparation_001/baseline_records.jsonl')
    base={r['proposition_id']:r for r in records}
    qpred=[dict(proposition_id=pid,verdict=r['verdict']) for pid,r in values.items() if r['status']=='success']
    bp=c.csvrows(c.OUT/'preparation_001/baseline_predictions.csv')
    op=c.csvrows(c.OUT/'preparation_001/old009_predictions.csv')
    rows=[dict(r,case_id=base[r['proposition_id']]['case_id'],baseline=base[r['proposition_id']]['baseline'],
        qwen=values[r['proposition_id']]['verdict'],qwen_status=values[r['proposition_id']]['status'],
        movement=movement(base[r['proposition_id']]['baseline'],values[r['proposition_id']]['verdict'],r['human_gt'])) for r in cohort]
    metrics={};patients=[];overlaps={};classrows=[];core=[];gates={}
    for author in ('llm','human'):
        own=[r for r in cohort if r['author_type']==author];ids={r['proposition_id'] for r in own}
        pred={name:[p for p in pp if p['proposition_id'] in ids] for name,pp in [('v4_010',bp),('qwen',qpred),('v4_009',op)]}
        metrics[author]={name:c.evaluate(own,p,iterations=1000,missing='error') if len(p)==len(own) else dict(status='blocked_missing',missing_ids=sorted(ids-{x['proposition_id'] for x in p})) for name,p in pred.items()}
        for name in ('v4_010','v4_009'):
            if len(pred['qwen'])==len(own):metrics[author]['qwen_minus_'+name]=c.paired_compare(own,pred[name],pred['qwen'],iterations=1000)
        rrows=[r for r in rows if r['author_type']==author]
        berr={r['proposition_id'] for r in rrows if r['baseline']!=r['human_gt']}
        qerr={r['proposition_id'] for r in rrows if r['qwen'] is not None and r['qwen']!=r['human_gt']}
        overlaps[author]=dict(n=len(own),v4_errors=len(berr),qwen_errors=len(qerr),intersection=len(berr&qerr),union=len(berr|qerr),
            jaccard=len(berr&qerr)/len(berr|qerr) if berr|qerr else None,
            intersection_over_v4_errors=len(berr&qerr)/len(berr) if berr else None,
            intersection_over_qwen_errors=len(berr&qerr)/len(qerr) if qerr else None,
            label_agreement=sum(r['baseline']==r['qwen'] for r in rrows)/len(own),
            movements=dict(Counter(r['movement'] for r in rrows)),
            both_wrong_same_label=sum(r['movement']=='both_wrong' and r['baseline']==r['qwen'] for r in rrows),
            both_wrong_different_label=sum(r['movement']=='both_wrong' and r['baseline']!=r['qwen'] for r in rrows),
            original_gt_confusion_counts=dict(Counter(r['human_gt']+' -> '+str(r['qwen']) for r in rrows if r['human_gt']!=r['qwen'])),
            full_prediction_coverage=len(pred['qwen'])==len(own))
        for model in ('v4_010','qwen','v4_009'):
            m=metrics[author][model]
            if 'n' not in m:continue
            core.append(dict(author=author,model=model,n=m['n'],pa=m['percent_agreement'],ac1=m['gwet_ac1'],mcc=m['mcc']))
            for label,v in m['per_class'].items():classrows.append(dict(author=author,model=model,label=label,**v))
        if 'qwen_minus_v4_010' in metrics[author]:
            diff=metrics[author]['qwen_minus_v4_010']['metrics']
            fp_delta=metrics[author]['qwen']['per_class']['Supported']['fp']-metrics[author]['v4_010']['per_class']['Supported']['fp']
            gates[author]=dict(delta_pa=diff['percent_agreement']['delta'],delta_mcc=diff['mcc']['delta'],false_supported_increase=fp_delta,
                meets_descriptive_nearness=diff['percent_agreement']['delta']>=-.03 and diff['mcc']['delta']>=-.05 and fp_delta/len(own)<=.02)
        for sid in sorted({r['subject_id'] for r in own}):
            subset=[r for r in own if r['subject_id']==sid];sids={r['proposition_id'] for r in subset}
            for model in ('v4_010','qwen'):
                pp=[p for p in pred[model] if p['proposition_id'] in sids]
                if len(pp)!=len(subset):continue
                m=c.evaluate(subset,pp,profile='none')
                patients.append(dict(subject_id=sid,author=author,model=model,n=m['n'],correct=sum(m['confusion_matrix'][i][i] for i in range(3)),
                    pa=m['percent_agreement'],ac1=m['gwet_ac1'],mcc=m['mcc'],mcc_denominator_zero=m['mcc_denominator_zero'],confusion_matrix=c.canonical(m['confusion_matrix'])))
    selected=select_cases(rows) if len(qpred)==650 else []
    output.mkdir(parents=True)
    c.write_json(output/'metrics.json',metrics);c.write_json(output/'overlap.json',overlaps);c.write_json(output/'nearness.json',gates)
    c.write_csv(output/'core_results.csv',core);c.write_csv(output/'classes.csv',classrows);c.write_csv(output/'patients.csv',patients)
    c.write_csv(output/'transitions.csv',rows);c.write_csv(output/'predictions_qwen.csv',qpred,['proposition_id','verdict'])
    c.write_csv(output/'attempts.csv',attempts)
    c.write_lines(output/'normalized_responses.jsonl',[dict(v,proposition_id=pid) for pid,v in values.items()])
    if selected:c.write_csv(output/'selected_cases.csv',selected)
    usage={}
    for model,ns in [('qwen',list(values.values())),('v4_010',[r['baseline_normalized'] for r in records])]:
        valid=[r for r in ns if r['status']=='success']
        usage[model]=dict(valid=len(valid),input_tokens=sum(r['usage']['input_tokens'] for r in valid),output_tokens=sum(r['usage']['output_tokens'] for r in valid),
            reasoning_tokens=sum(r['usage']['reasoning_tokens'] for r in valid),adherence_flagged=sum(bool(r['adherence_errors']) for r in valid),
            adherence_flags=dict(Counter(e for r in valid for e in r['adherence_errors'])),
            mean_latency_seconds=statistics.mean(r['latency_seconds'] for r in valid) if valid else None,
            median_latency_seconds=statistics.median(r['latency_seconds'] for r in valid) if valid else None,
            returned_models=dict(Counter(r.get('model_returned') for r in valid)))
    summary=dict(claims=650,valid_qwen=len(qpred),failed=[dict(v,proposition_id=pid) for pid,v in values.items() if v['status']!='success'],
        task_cost_or_reserved_cny=sum(r['charge_cny'] for r in attempts),http_attempts=len(attempts),http_status_counts=dict(Counter(r['http_status'] for r in attempts)),
        accounts=dict(Counter(r['account'] for r in attempts)),usage=usage,selected_semantic_cases=len(selected),
        qwen_start=min(r['started_utc'] for r in attempts if r['started_utc']),qwen_end=max(r['ended_utc'] for r in attempts if r['ended_utc']),
        nearness_both_authors=bool(len(gates)==2 and all(g['meets_descriptive_nearness'] for g in gates.values())),
        historical_not_concurrent=True,independent_audit=False)
    c.write_json(output/'summary.json',summary)
    packets=output/'cases';packets.mkdir()
    for r in selected:
        br=base[r['proposition_id']];data=c.pilot.strict_json(br['baseline_body']['messages'][1]['content'])
        packet=dict(row=r,claim=data['proposition'],reference=data['reference'],v4_output=br['baseline_normalized']['output_text'],qwen_output=values[r['proposition_id']]['output_text'])
        c.write_json(packets/(r['case_id']+'.json'),packet)
    c.write_json(output/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in output.rglob('*') if p.is_file()},
        code_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [Path(__file__),c.TASK/'common014.py']},
        dependencies={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [c.OUT/'preparation_001/manifest.json',c.OUT/'live/state.json']}))
    print(c.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'analysis_001');analyze(p.parse_args().output.resolve())
