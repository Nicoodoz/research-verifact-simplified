"""One-time navigation and audit snapshot; no API or secret loading."""
import subprocess,sys,platform,importlib.metadata,datetime
import common028 as c

def prepend(relative,entry):
    path=c.ROOT/relative;raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';first,rest=raw.split(nl,1)
    c.require('028当前'.encode() not in raw,'Already synchronized')
    path.write_bytes(first+nl+nl+entry.encode('utf-8')+nl+rest)

def run():
    c.require(not (c.OUT/'handoff_001.json').exists(),'Handoff frozen');c.verify_inputs()
    report=c.OUT/'report.md';raw=report.read_bytes();report.write_bytes(raw.replace('AC10.7208'.encode(),'AC1为0.7208'.encode()))
    note='**028当前（2026-09-19）：** 可追溯主张—证据核查执行及自检完成，待独立审计。155个development候选，两臂各155次核心有效；trace仅保留44/110真S救回，相对SD完整队列净−40，相对repeat+9但区间跨0。未稳定超过完整global-λ参考，停止当前语义核查版本。费用估算3.798027/80元，不改λ/C48/历史结果，不自动029或reserved40。'
    for rel,prefix in [('README.md',''),('AGENTS.md',''),('docs/PROJECT_STATUS.md','../')]:
        prepend(rel,note+f' [主报告]({prefix}outputs/028_traceable_claim_evidence_verification/report.md) · [交审]({prefix}outputs/028_traceable_claim_evidence_verification/audit_handoff.md)。')
    prepend('docs/REPRODUCIBILITY.md','**028当前离线入口（执行自检完成，待独立审计）：** `python -B tasks/028_traceable_claim_evidence_verification/replay028.py outputs/replays/<new-directory>`；禁网，从回执核对16份正式机器结果。只读核查为 `verify028.py outputs/028_traceable_claim_evidence_verification/<new-directory>`；禁止用收费runner重放。[交审](../outputs/028_traceable_claim_evidence_verification/audit_handoff.md)。')
    replay=c.ROOT/'outputs/replays/028_self_replay_001/replay_check.json'
    c.put(c.OUT/'verification_001/replay_summary.json',dict(source=replay.relative_to(c.ROOT).as_posix(),sha256=c.sha(replay),result=c.read(replay)))
    c.put(c.OUT/'environment_001.json',dict(python=sys.version,platform=platform.platform(),packages={k:importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','pandas')},figure_environment='research / Matplotlib3.5.1',API_requests=310,new_fits=0))
    paths=set(p for folder in (c.TASK,c.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for folder in ('analysis_001','diagnosis_001','semantic_001','verification_001'):
        m=c.read(c.OUT/folder/'manifest.json')
        for p,h in m['inputs'].items():c.require(c.sha(c.ROOT/p)==h,'Input changed '+p);paths.add(c.ROOT/p)
        for p,h in m['outputs'].items():c.require(c.sha(c.OUT/folder/p)==h,'Output changed '+p)
    for task in ('024_lambda2_transfer_validation','025_lambda_flip_risk_separability','026_frozen_sd_patient_transfer','027_dual_judge_transfer_diagnosis'):
        paths.update((c.ROOT/'tasks'/task).glob('*.py'))
    paths.update((c.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'];paths.update(c.ROOT/p for p in docs+['environment.yml'])
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();c.require(set(changed)<=set(docs),'Historical tracked files changed')
    c.put(c.OUT/'handoff_001.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=c.ROOT,text=True).splitlines(),tracked_modified=changed,API_requests=310,new_fits=0,cost_cny=3.798027,unknown_reserve_cny=0,reserved_case_access=False,independent_audit='pending',stop_current_method=True,sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sorted(paths)}))
    print('028 handoff frozen:',len(paths),'fingerprints; independent audit pending')

if __name__=='__main__':run()
