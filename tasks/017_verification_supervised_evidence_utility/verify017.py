"""Offline replay. Never calls an API or changes frozen017 outputs."""
from pathlib import Path
import argparse
import subprocess
import common017 as c
from selection017 import interventions
from analyze017 import analyze

MUTABLE={'.gitattributes','README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','reviews/README.md','docs/aliyun/CURRENT.md'}

def verify(out):
    c.require(not out.exists(),'Verification output already exists')
    c.require(not (c.OUT/'task_api.lock').exists(),'Finish API execution first')
    prep=c.OUT/'preparation_001';analysis=c.OUT/'analysis_001'
    c.check(prep);c.check(analysis)
    auth=c.read(c.OUT/'authority_001.json')
    c.old.check_hashes(auth['execution_sha256'])
    c.old.check_hashes(c.read(c.OUT/'analysis_plan_001.json')['code_sha256'])
    c.require(c.file_hash(c.OUT/'protocol_001.md')==auth['protocol_sha256'],'Protocol changed')
    c.require(c.file_hash(c.OUT/'execution_policy_001.json')==auth['execution_policy_sha256'],'Execution policy changed')
    rows,passages,_=c.sources();byid={r['proposition_id']:r for r in rows}
    order=c.old.baseline.patient_order();ids=[]
    for sid in order[18:30]:
        for author in ('llm','human'):
            ids += [r['proposition_id'] for r in sorted([r for r in rows if r['subject_id']==sid and r['author_type']==author],key=lambda r:c.rank_id(r['proposition_id']))[:8]]
    records=c.jsonlines(prep/'inputs.jsonl')
    c.require(ids==[r['proposition_id'] for r in records],'GT-blind sampling differs')
    c.require(set(order[18:24]).isdisjoint(order[24:30]) and set(order[18:30]).isdisjoint(order[30:]),'Patient split overlap')
    jobs={};assignments=[];prompts=c.read(prep/'judge_prompts.json')
    for item in records:
        original=byid[item['proposition_id']]
        arms=interventions(original,passages)
        c.require(item==dict(original,interventions=arms),'Frozen action/feature reconstruction differs')
        for arm,r in arms.items():
            body=c.old.judge_body(original,r['reference'],prompts,'v4_first')
            for repeat in (0,1):
                rid=f'017:headroom:r{repeat}:'+c.fingerprint(body)
                jobs.setdefault(rid,dict(request_id=rid,kind='chat',body=body,proposition_id=original['proposition_id'],case_id=original['case_id']))
                assignments.append(dict(proposition_id=original['proposition_id'],case_id=original['case_id'],arm=arm,repeat=str(repeat),request_id=rid,body_sha256=c.fingerprint(body)))
    c.require(jobs=={j['request_id']:j for j in c.jsonlines(prep/'jobs.jsonl')},'Request reconstruction differs')
    c.require(assignments==c.csvrows(prep/'assignments.csv'),'Logical cache bindings differ')
    cohort=c.gt_for(set(ids));c.require(cohort==c.csvrows(c.OUT/'evaluation_cohort.csv'),'Evaluation cohort differs from frozen sources')
    c.require(all(r['invalid']=='False' and r['proposition_type']=='claim' and r['human_gt'] in c.LABELS for r in cohort),'Expected valid atomic claims only')
    history=c.read(c.OUT/'history_before.json');changed=[];protected=0
    for name,sha in history['files'].items():
        p=c.ROOT/name
        if not p.exists() or c.file_hash(p)!=sha:
            c.require(name in MUTABLE,'Protected pre017 file changed: '+name);changed.append(name)
        else:protected+=1
    out.mkdir(parents=True);replay=out/'analysis_replay';analyze(replay)
    canonical={p.relative_to(analysis).as_posix():c.file_hash(p) for p in analysis.rglob('*') if p.is_file() and p.name!='manifest.json'}
    rerun={p.relative_to(replay).as_posix():c.file_hash(p) for p in replay.rglob('*') if p.is_file() and p.name!='manifest.json'}
    c.require(canonical==rerun,'Receipt-only scoring replay differs')
    gate=c.read(analysis/'gate.json')
    if not gate['passed']:
        c.require(not (c.OUT/'learning_001').exists(),'Training performed after failed headroom gate')
        c.require(not (c.OUT/'confirmation_001').exists(),'Confirmation performed after failed headroom gate')
    result=dict(status='execution_self_check_passed_not_independent_audit',claims=len(records),reconstructed_requests=len(jobs),
        logical_conditions=len(assignments),byte_identical_analysis_files=len(canonical),protected_history_files=protected,
        changed_mutable_navigation=changed,history_HEAD=history['HEAD'],HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
        no_API_called=True,new10_clinical_data_used=False,reserved_test_used=False)
    c.write_json(out/'summary.json',result)
    c.seal(out,[prep/'manifest.json',analysis/'manifest.json',c.OUT/'authority_001.json',c.OUT/'analysis_plan_001.json'],[Path(__file__)])
    print(c.canonical(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'verification_001');verify(p.parse_args().output.resolve())
