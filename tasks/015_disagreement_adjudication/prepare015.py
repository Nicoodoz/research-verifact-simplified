"""Verify 014 actual receipts; freeze screened cohort, oracle and GT-free request payloads."""
import hashlib
import subprocess
from collections import Counter
import common015 as c
import analyze014

def prepare():
    out=c.OUT/'preparation_001';c.require(not out.exists(),'Preparation exists')
    values,_=analyze014.load_results()
    rows=c.csvrows(c.prior.OUT/'analysis_001/transitions.csv')
    base={r['proposition_id']:r for r in c.jsonlines(c.prior.OUT/'preparation_001/baseline_records.jsonl')}
    c.require(len(rows)==len(base)==len(values)==650,'Wrong size')
    for r in rows:
        pid=r['proposition_id'];v=values[pid]
        c.require(v['status']=='success' and v['verdict']==r['qwen'],'Qwen receipt mismatch')
        c.require(base[pid]['baseline']==r['baseline'],'V4 mismatch')
        for key in ('subject_id','author_type','human_gt','invalid','proposition_type'):
            c.require(base[pid][key]==r[key],'Cohort mismatch '+key)
        r['bucket']=c.bucket(r)
    groups=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')
    order=sorted(groups['groups']['development'],key=lambda x:hashlib.sha256((groups['seed']+x).encode()).hexdigest())
    c.require({r['subject_id'] for r in rows}==set(order[18:24]),'Wrong patients')
    cohort=c.csvrows(c.prior.OUT/'preparation_001/cohort.csv')
    for a in ('llm','human'):
        own=[r for r in cohort if r['author_type']==a]
        for key,model in [('baseline','v4_010'),('qwen','qwen')]:
            pred=[dict(proposition_id=r['proposition_id'],verdict=r[key]) for r in rows if r['author_type']==a]
            m=c.evaluate(own,pred,iterations=1000)
            c.require(m==c.read(c.prior.OUT/'analysis_001/metrics.json')[a][model],'014 metrics mismatch')
    oracle={}
    for a in ('llm','human','all'):
        rr=[r for r in rows if a=='all' or r['author_type']==a]
        oracle[a]=dict(n=len(rr),disagreements=sum(r['baseline']!=r['qwen'] for r in rr),
            bucket_counts=dict(Counter(c.bucket(r) for r in rr)),v4_correct=c.correct(rr,'baseline'),qwen_correct=c.correct(rr,'qwen'),
            best_single_correct=max(c.correct(rr,k) for k in ('baseline','qwen')),
            selection_oracle_correct=sum(r['human_gt'] in (r['baseline'],r['qwen']) for r in rr),
            free_label_oracle_correct=sum(r['baseline']!=r['qwen'] or r['baseline']==r['human_gt'] for r in rr),
            agreement_both_wrong=sum(r['baseline']==r['qwen']!=r['human_gt'] for r in rr))
    jobs=[];opinions=[];disagreements=[r for r in rows if r['baseline']!=r['qwen']]
    for r in disagreements:
        pid=r['proposition_id'];b=base[pid];v=values[pid]
        opinions.append(dict(proposition_id=pid,case_id=r['case_id'],base_body=b['baseline_body'],
            v4_output=b['baseline_normalized']['output_text'],qwen_output=v['output_text'],candidate_order=c.candidate_order(pid)))
        for arm in c.ARMS:
            body=c.build_body(b['baseline_body'],pid,b['baseline_normalized']['output_text'],v['output_text'],arm)
            jobs.append(dict(request_id='015:'+c.fingerprint(body),case_id=r['case_id'],proposition_id=pid,arm=arm,body=body))
    jobs.sort(key=lambda j:hashlib.sha256(('015/request/v1:'+j['request_id']).encode()).hexdigest())
    c.require(len(jobs)==len({j['request_id'] for j in jobs})==156,'Unexpected jobs/duplicate bodies')
    estimate=sum((sum(len(m['content']) for m in j['body']['messages'])*.4*3+450*9)/1e6 for j in jobs)
    out.mkdir(parents=True)
    for name in ('cohort.csv','baseline_predictions.csv'):(out/name).write_bytes((c.prior.OUT/'preparation_001'/name).read_bytes())
    (out/'qwen_predictions.csv').write_bytes((c.prior.OUT/'analysis_001/predictions_qwen.csv').read_bytes())
    c.write_csv(out/'ledger.csv',rows);c.write_csv(out/'disagreements.csv',disagreements)
    c.write_json(out/'oracle.json',oracle);c.write_lines(out/'jobs.jsonl',jobs);c.write_lines(out/'candidate_sources.jsonl',opinions)
    c.write_json(out/'summary.json',dict(claims=650,disagreements=len(disagreements),new_requests=len(jobs),
        patient_ids=sorted({r['subject_id'] for r in rows}),estimate_screening_cny=estimate,
        all_single_attempt_reservations=sum(c.bound(j) for j in jobs),
        candidate_A_source_counts=dict(Counter(o['candidate_order'][0] for o in opinions)),
        conditionally_confirm_patient_ids=order[24:30],confirmation_not_started=True))
    c.write_json(c.OUT/'authority_001.json',dict(created_utc=c.now(),task_cap_cny=40,screening_planning_cny=3,
        conditional_whole_task_planning_cny=30,authority='User task 015 real adjudication and conditional confirmation; AGENTS standing <=40 CNY rule',
        start_account='account_2',current_phase='screening_only',invoice_verified=False))
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=c.ROOT).decode().split('\0')
    history={n:c.file_hash(c.ROOT/n) for n in tracked if n and n not in ('README.md','AGENTS.md')}
    c.write_json(out/'history_sha256.json',history)
    deps=[c.prior.OUT/'preparation_001/manifest.json',c.prior.OUT/'analysis_001/metrics.json',c.prior.OUT/'live/state.json',
        c.prior.OUT/'analysis_001/transitions.csv',c.ROOT/'outputs/003_error_analysis/patient_groups.json']
    deps+=list((c.prior.OUT/'live').glob('receipt_*.json'))
    code=[c.TASK/n for n in ('common015.py','prepare015.py','run015.py')]
    code+=[c.prior.TASK/'common014.py',c.prior.TASK/'analyze014.py',c.ROOT/'src/verifact_research/inference/siliconflow_pool.py',
        c.ROOT/'tasks/004_event_alignment_pilot/pilot.py',c.ROOT/'tasks/004_event_alignment_pilot/siliconflow.py']
    code+=list((c.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    c.write_json(out/'manifest.json',dict(created_utc=c.now(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT).decode().strip(),
        files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in out.iterdir() if p.is_file()},
        dependencies={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in deps},execution_code={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},
        protocol_sha256=c.file_hash(c.OUT/'protocol_001.md'),authority_sha256=c.file_hash(c.OUT/'authority_001.json')))
    print(c.canonical(c.read(out/'summary.json')))

if __name__=='__main__':prepare()
