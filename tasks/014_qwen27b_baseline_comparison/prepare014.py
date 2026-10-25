"""Copy exact 010 C48 bodies, bind old canonical receipts and protect history."""
import copy
import subprocess
import common014 as c

def prepare():
    out = c.OUT/'preparation_001'
    c.require(not out.exists(), 'Preparation already exists')
    deps = {}
    def bind(p):
        deps[p.relative_to(c.ROOT).as_posix()] = c.file_hash(p)
    for folder in (c.OLD/'preparation_001', c.OLD/'analysis_001'):
        m = c.read(folder/'manifest.json')
        for name,h in m['files'].items():
            c.require(c.file_hash(folder/name)==h, '010 artifact changed: '+name)
            bind(folder/name)
        bind(folder/'manifest.json')
    groups = c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')
    bind(c.ROOT/'outputs/003_error_analysis/patient_groups.json')
    order = sorted(groups['groups']['development'], key=lambda x:c.fingerprint(x))
    import hashlib
    order = sorted(groups['groups']['development'], key=lambda x:hashlib.sha256((groups['seed']+x).encode()).hexdigest())
    rows = c.csvrows(c.OLD/'preparation_001/cohort.csv')
    c.require(len(rows)==len({r['proposition_id'] for r in rows})==650, 'Wrong cohort')
    c.require({r['subject_id'] for r in rows}==set(order[18:24]), 'Wrong patients')
    c.require(all(r['invalid']=='False' and r['proposition_type']=='claim' for r in rows), 'Wrong validity')
    inputs = {r['proposition_id']:r for r in c.jsonlines(c.OLD/'preparation_001/inputs.jsonl')}
    baseline = {r['proposition_id']:r['verdict'] for r in c.csvrows(c.OLD/'analysis_001/predictions_c48_reference.csv')}
    assignments = {r['proposition_id']:r for r in c.csvrows(c.OLD/'preparation_001/assignments.csv') if r['arm']=='c48_reference'}
    manifest = c.read(c.OLD/'live/judge/manifest.json')
    state = c.read(c.OLD/'live/judge/state.json')
    c.require(state['run_id']==c.fingerprint(manifest), 'Old run identity')
    for name in ('manifest.json','state.json'):
        bind(c.OLD/'live/judge'/name)
    oldjobs = {j['request_id']:j for j in manifest['jobs']}
    # Verify claim and labels against the existing 002 index; only selected text read from raw.
    masterpath = c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv'
    master = {r['proposition_id']:r for r in c.csvrows(masterpath)}
    bind(masterpath)
    rawpath=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/propositions/propositions.csv.gz'
    formal=c.read(c.ROOT/'outputs/002_reproduce_paper_results/run_003/manifest.json')
    c.require(c.file_hash(rawpath)==formal['input_sha256']['propositions/propositions.csv.gz'],'Raw propositions changed')
    props={r['proposition_id']:r for r in c.pilot.subset_csv(rawpath,'proposition_id',set(baseline))}
    bind(rawpath)
    old009path=c.ROOT/'outputs/009_retrieval_baselines/confirmation_001/analysis_001/predictions_C48.csv'
    bind(old009path)
    records,jobs=[],[]
    for row in rows:
        pid=row['proposition_id']; a=assignments[pid]; item=inputs[pid]
        for k in ('subject_id','hadm_id','human_gt','invalid','author_type','proposition_type'):
            c.require(row[k]==master[pid][k], '002 cohort mismatch '+k)
        c.require(item['text']==props[pid]['text'], 'Claim changed')
        oldjob=oldjobs[a['request_id']]
        body=oldjob['body']
        c.require(c.fingerprint(body)==a['body_sha256']==item['previous_c48_body_sha256'], 'Body mismatch')
        message=c.pilot.strict_json(body['messages'][1]['content'])
        c.require(message==dict(proposition=item['text'],reference=item['references']['c48_reference']), 'Wrong claim/reference fields')
        ptrs=state['jobs'][a['request_id']]['receipts']
        successful=[]
        for ptr in ptrs:
            path=c.OLD/'live/judge'/ptr['file']
            c.require(c.file_hash(path)==ptr['sha256'], 'Old receipt changed')
            receipt=c.read(path)
            c.require(receipt['run_id']==state['run_id'] and receipt['job_sha256']==c.fingerprint(oldjob), 'Old receipt binding')
            bind(path)
            if receipt['transport']['http_status']==200:
                successful.append((path,receipt))
        c.require(len(successful)==1, 'Old canonical missing/duplicated')
        path,receipt=successful[0]
        oldnorm=c.normalize(dict(oldjob,proposition_id=pid),receipt,c.V4)
        c.require(oldnorm['status']=='success' and oldnorm['verdict']==baseline[pid], 'Old label differs')
        newbody=copy.deepcopy(body); newbody['model']=c.MODEL
        job=dict(request_id='qwen:'+c.fingerprint(newbody),proposition_id=pid,case_id=item['case_id'],body=newbody)
        c.require({k:v for k,v in body.items() if k!='model'}=={k:v for k,v in newbody.items() if k!='model'}, 'Extra intervention')
        jobs.append(job)
        records.append(dict(row,case_id=item['case_id'],baseline=baseline[pid],baseline_request_id=a['request_id'],
            baseline_receipt=path.relative_to(c.ROOT).as_posix(),baseline_body=body,baseline_normalized=oldnorm,
            qwen_request_id=job['request_id'],qwen_body_sha256=c.fingerprint(newbody)))
    c.require(len({j['request_id'] for j in jobs})==650, 'Unexpected duplicate full body')
    jobs.sort(key=lambda j:hashlib.sha256(('014/order/v1:'+j['proposition_id']).encode()).hexdigest())
    out.mkdir(parents=True)
    (out/'cohort.csv').write_bytes((c.OLD/'preparation_001/cohort.csv').read_bytes())
    (out/'baseline_predictions.csv').write_bytes((c.OLD/'analysis_001/predictions_c48_reference.csv').read_bytes())
    (out/'old009_predictions.csv').write_bytes(old009path.read_bytes())
    c.write_lines(out/'baseline_records.jsonl',records)
    c.write_lines(out/'jobs.jsonl',jobs)
    estimate=sum((sum(len(m['content']) for m in j['body']['messages'])*.4*3+400*12)/1e6 for j in jobs)
    summary=dict(claims=650,authors={a:sum(r['author_type']==a for r in rows) for a in ('llm','human')},
        patient_ids=sorted(set(r['subject_id'] for r in rows)),new_requests=650,baseline_source='010 canonical C48',
        only_model_changed=True,estimated_cny=estimate,planning_cny=12,all_single_attempt_byte_reservations=sum(c.bound(j) for j in jobs),
        context_byte_bound_max=max(len(c.canonical(j['body']).encode())+2000 for j in jobs))
    c.require(estimate<40, 'Cannot authorize task forecast')
    c.write_json(out/'summary.json',summary)
    auth=dict(created_utc=c.now(),source='User requested task 014 and real Qwen API; AGENTS standing <=40 CNY authority',
        expected_total_cny=12,task_cap_cny=40,input_rate_per_million=3,output_rate_per_million=12,
        first_account='account_2',scope='650 Qwen canonical only, necessary retries; no new V4',invoice_verified=False)
    c.write_json(c.OUT/'authority_001.json',auth)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=c.ROOT).decode().split('\0')
    protected={n:c.file_hash(c.ROOT/n) for n in tracked if n and not n.startswith(('tasks/014_','outputs/014_')) and n not in ('README.md','AGENTS.md')}
    c.write_json(out/'history_sha256.json',protected)
    code=[c.TASK/'common014.py',c.TASK/'prepare014.py',c.TASK/'run014.py',c.ROOT/'tasks/004_event_alignment_pilot/pilot.py',c.ROOT/'tasks/004_event_alignment_pilot/siliconflow.py',c.ROOT/'src/verifact_research/inference/siliconflow_pool.py']
    code+=list((c.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    c.write_json(out/'manifest.json',dict(created_utc=c.now(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT).decode().strip(),
        files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in out.iterdir() if p.is_file()},dependencies=deps,
        execution_code={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in code},
        authority_sha256=c.file_hash(c.OUT/'authority_001.json'),protocol_sha256=c.file_hash(c.OUT/'protocol_001.md')))
    print(c.canonical(summary))

if __name__=='__main__':
    prepare()
