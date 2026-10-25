"""One-time navigation and final audit snapshot. No secret or API access."""
import subprocess,sys,platform,importlib.metadata,datetime
from pathlib import Path
import common027 as x

def prepend(relative,entry):
    path=x.ROOT/relative;raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';first,rest=raw.split(nl,1);x.c.require('027当前'.encode() not in raw,'Already synchronized');path.write_bytes(first+nl+nl+entry.encode('utf-8')+nl+rest)

def run():
    x.offline();x.c.require(not (x.OUT/'handoff_001.json').exists(),'Handoff frozen')
    note='**027当前（2026-09-19）：** 双Judge迁移瓶颈离线诊断完成，执行自检通过，待独立审计。026排序仍有信息，但≥80% rescue区对完整global混合包络最多+2.368R，不能仅换阈值恢复门槛；22/52候选存在精确输入冲突。组成与概率尺度变化并存，现有证据不足以支持仅改工作点／融合器继续救Gate。0 API、0新增拟合、不改λ、不用reserved40，完成后停止。'
    for rel,prefix in [('README.md',''),('AGENTS.md',''),('docs/PROJECT_STATUS.md','../')]:prepend(rel,note+f' [主报告]({prefix}outputs/027_dual_judge_transfer_diagnosis/report.md) · [交审]({prefix}outputs/027_dual_judge_transfer_diagnosis/audit_handoff.md)。')
    prepend('docs/REPRODUCIBILITY.md','**027当前离线入口（执行自检完成，待独立审计）：** `python -B tasks/027_dual_judge_transfer_diagnosis/replay027.py outputs/replays/<new-directory>`；禁网、禁止新拟合，核对11个正式文件。正式analysis_002／figures_002；[交审](../outputs/027_dual_judge_transfer_diagnosis/audit_handoff.md)说明概率来源、完整global及病例诊断边界。')
    replay=x.ROOT/'outputs/replays/027_self_replay_001/replay_check.json';x.put(x.OUT/'verification_001/replay_summary.json',dict(source=replay.relative_to(x.ROOT).as_posix(),sha256=x.sha(replay),result=x.read(replay)))
    x.put(x.OUT/'environment_001.json',dict(python=sys.version,platform=platform.platform(),packages={k:importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','pandas')},figure_environment='research / Matplotlib3.5.1',API_calls=0,new_fits=0))
    paths=set(p for folder in (x.TASK,x.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for folder in ('analysis_001','analysis_002','case_material_001','reading_view_001','semantic_001','interpretation_001','verification_001'):
        m=x.read(x.OUT/folder/'manifest.json')
        for p,h in m['inputs'].items():x.c.require(x.sha(x.ROOT/p)==h,'Input changed '+p);paths.add(x.ROOT/p)
        for p,h in m['outputs'].items():x.c.require(x.sha(x.OUT/folder/p)==h,'Output changed '+p)
    for n in ('025_lambda_flip_risk_separability','022_competition_aware_support_calibration'):
        paths.update((x.ROOT/'tasks'/n).glob('*.py'))
    paths.update((x.ROOT/'src/verifact_research/evaluation').glob('*.py'))
    docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'];paths.update(x.ROOT/p for p in docs+['environment.yml'])
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=x.ROOT,text=True).splitlines();x.c.require(set(changed)<=set(docs),'Historical tracked files changed')
    x.put(x.OUT/'handoff_001.json',dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=x.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=x.ROOT,text=True),untracked=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=x.ROOT,text=True).splitlines(),tracked_modified=changed,API_calls=0,new_fits=0,cost_cny=0,reserved_case_access=False,independent_audit='pending',no_new_winner=True,sha256={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in sorted(paths)}))
    print('027 handoff frozen:',len(paths),'fingerprints; independent audit pending')
if __name__=='__main__':run()
