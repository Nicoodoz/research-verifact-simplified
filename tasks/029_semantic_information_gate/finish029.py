"""One-time final navigation and handoff snapshot; no fitting or API."""
import subprocess
import common029 as c

def prepend(relative,entry):
    path=c.ROOT/relative;raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';c.require('029当前'.encode() not in raw,'Navigation already synchronized');first,rest=raw.split(nl,1);path.write_bytes(first+nl+nl+entry.encode('utf-8')+nl+rest)

def run():
    c.offline();c.require(not (c.OUT/'handoff_001.json').exists(),'Handoff already frozen');c.verify_frozen()
    for base in (c.OUT/'run_001',c.OUT/'closeout_001'):
        manifest=c.read(base/'manifest.json')
        for rel,h in manifest.get('files',manifest.get('outputs',{})).items():c.require(c.sha(base/rel)==h,'Completed artifact changed '+rel)
        for rel,h in manifest.get('inputs',{}).items():c.require(c.sha(c.ROOT/rel)==h,'Closeout source changed '+rel)
    c.require(not subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).strip(),'Unexpected tracked edits before navigation')
    note='**029当前（2026-09-20）：** 离线36组实验及执行者收尾完成，待独立审计。联合repeat+trace的Logistic在患者OOF相对A/B同风险混合包络多11/9R，保留该开发信号；反向迁移保留率71.1%，优势未稳定复现，XGBoost无可靠补救。不选winner、不继续特征/分类器搜索、不自动030或reserved40；0 API、0费用，独立029环境，未改历史结果。'
    for rel,prefix in [('README.md',''),('AGENTS.md',''),('docs/PROJECT_STATUS.md','../')]:prepend(rel,note+f' [主报告]({prefix}outputs/029_semantic_information_gate/report.md) · [交审]({prefix}outputs/029_semantic_information_gate/audit_handoff.md)。')
    prepend('docs/REPRODUCIBILITY.md','**029当前离线入口（执行者收尾完成，待独立审计）：** 独立环境`research-verifact-029`运行`python -B tasks/029_semantic_information_gate/run029.py --run-id <new-id>`，禁止覆盖run_001。该入口离线重训固定条件，0 API，不修改原环境；收尾核验另重算3096个保存模型状态、0次拟合。[交审](../outputs/029_semantic_information_gate/audit_handoff.md)含完整命令、固定预测bootstrap及辅助检查的工作区前提。')
    docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'];changes=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();c.require(set(changes)==set(docs),'Unexpected tracked edits')
    paths={p for folder in (c.TASK,c.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for section in ('sources','files','code'):
        paths.update(c.ROOT/p for p in c.read(c.PREP/'manifest.json')[section])
    paths.update(c.ROOT/p for p in docs+['environment.yml'])
    c.put(c.OUT/'handoff_001.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),tracked_modified=changes,API_calls=0,cost_cny=0,independent_audit='pending',no_winner_selected=True,no_automatic_followup=True,sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sorted(paths)}));print('029 handoff:',len(paths),'fingerprints; independent audit pending')

if __name__=='__main__':run()
