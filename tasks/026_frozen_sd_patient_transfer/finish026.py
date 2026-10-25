"""One-time current-navigation update and executor audit snapshot; no API sends."""
import subprocess
from pathlib import Path
import common026 as c

def run():
    c.require(not (c.OUT/'handoff_001.json').exists(),'Handoff already frozen')
    c.verify_inputs()
    note='**026当前（2026-09-19）：** 冻结SD跨患者组迁移已完成执行与自检，待独立审计。6人650条，D评分/B各650，仅52个候选调用Qwen；1352个核心有效，费用估算16.782714/80元。SD保留29/34救回、新增false-S18→12，但相对完整global随机混合包络仅+2.11R，留一患者4/6为正，未达事前门槛；停止当前版本，不调参、不自动reserved40。'
    for rel,prefix in [('README.md',''),('AGENTS.md',''),('docs/PROJECT_STATUS.md','../')]:
        path=c.ROOT/rel;raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';first,rest=raw.split(nl,1)
        c.require('026当前'.encode() not in raw,'026 navigation already present')
        addition=note+f' [主报告]({prefix}outputs/026_frozen_sd_patient_transfer/report.md) · [交审]({prefix}outputs/026_frozen_sd_patient_transfer/audit_handoff.md)。'
        path.write_bytes(first+nl+nl+addition.encode('utf-8')+nl+rest)
    path=c.ROOT/'docs/REPRODUCIBILITY.md';raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';first,rest=raw.split(nl,1)
    entry='**026当前离线入口（执行自检完成，待独立审计）：** `python -B tasks/026_frozen_sd_patient_transfer/replay026.py outputs/replays/<new-directory>`；禁网、新目录、校验15个机器结果。只读来源核查：`verify026.py outputs/026_frozen_sd_patient_transfer/<new-verification-directory>`。禁止使用收费runner做重放。冻结SD未达迁移门槛，已停止；[主报告](../outputs/026_frozen_sd_patient_transfer/report.md) · [交审](../outputs/026_frozen_sd_patient_transfer/audit_handoff.md)。'
    path.write_bytes(first+nl+nl+entry.encode('utf-8')+nl+rest)
    replay=c.ROOT/'outputs/replays/026_self_replay_001/replay_check.json'
    c.put(c.OUT/'verification_001/replay_summary.json',dict(source=replay.relative_to(c.ROOT).as_posix(),source_sha256=c.sha(replay),result=c.read(replay)))
    files=sorted([p for folder in (c.TASK,c.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts])
    # Exact secret comparison in memory; never write or print a key.
    secret=c.load_config(c.ROOT/'.env.aliyun').api_key.encode('utf-8')
    c.require(bool(secret) and not any(secret in p.read_bytes() for p in files),'Secret scan failed')
    deps=set()
    for name in ('gate_freeze/manifest.json','preparation_001/manifest.json','candidate_freeze/manifest.json','analysis_001/manifest.json','supplement_001/manifest.json','verification_001/manifest.json'):
        deps.update(c.ROOT/p for p in c.read(c.OUT/name)['sha256'])
    for n in ('019_support_boundary_screen','020_lambda2_patient_validation','022_competition_aware_support_calibration','024_lambda2_transfer_validation','025_lambda_flip_risk_separability'):
        deps.update((c.ROOT/'tasks'/n).glob('*.py'))
    deps.update((c.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    deps.update(c.ROOT/p for p in ('README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md','environment.yml','reviews/024_lambda2_transfer_validation.md','reviews/025_lambda_flip_risk_separability.md'))
    tracked=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines()
    c.require(set(tracked)<=set(['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md']),'Unexpected historical modification')
    c.put(c.OUT/'handoff_001.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),tracked_modified=tracked,untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=c.ROOT,text=True).splitlines(),executor_self_check=True,independent_audit='pending',task_decision='stop_frozen_SD_transfer_threshold_not_met',api_calls=1352,total_cost_estimate_cny=16.782714,api_cap_cny=80,exact_active_key_scan='no_match_in_task_artifacts',sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sorted(set(files)|deps)}))
    print(c.canonical(dict(handoff='outputs/026_frozen_sd_patient_transfer/handoff_001.json',files=len(files),independent_audit='pending',historical_files_unchanged=True)))
if __name__=='__main__':run()
