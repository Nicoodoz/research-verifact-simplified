"""One-time documentation navigation and handoff, no new experiment."""
import subprocess
import common030 as c
def prepend(rel,entry):
    p=c.ROOT/rel;raw=p.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';c.require('030当前'.encode() not in raw,'Navigation already updated');first,rest=raw.split(nl,1);p.write_bytes(first+nl+nl+entry.encode()+nl+rest)
def main():
    c.offline();c.require(not (c.OUT/'handoff_001.json').exists(),'Handoff frozen');c.verify()
    for base in (c.OUT/'run_001',c.OUT/'closeout_001'):
        m=c.read(base/'manifest.json')
        for rel,h in m.get('files',m.get('outputs',{})).items():c.require(c.sha(base/rel)==h,'Result modified '+rel)
        for rel,h in m.get('inputs',{}).items():c.require(c.sha(c.ROOT/rel)==h,'Closeout source changed '+rel)
    c.require(not subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).strip(),'Unexpected tracked edits')
    note='**030当前（2026-09-20）：** 固定Gate训练规模/组成分析执行及收尾完成，待独立审计。141个不同评价轮次，4356最终模型；11人训练时D对A/B合并平均同风险+5.11/+3.83R，但025子组仍多次反向、D更敏感。14人仅复现029锚点，不能据零波动证明组成稳健；现有数据不足以确定稳定最低人数或来源配比。0 API，不自动扩大训练材料、031或reserved40。'
    for rel,prefix in [('README.md',''),('AGENTS.md',''),('docs/PROJECT_STATUS.md','../')]:prepend(rel,note+f' [主报告]({prefix}outputs/030_gate_training_stability/report.md) · [交审]({prefix}outputs/030_gate_training_stability/audit_handoff.md)。')
    prepend('docs/REPRODUCIBILITY.md','**030当前离线入口（收尾完成，待独立审计）：** 独立research-verifact-029环境；只读核验`close030.py outputs/030_gate_training_stability/<new-directory>`，重算保存模型不拟合；完整重训`run030.py --run-id <new-id>`，禁止覆盖run_001。[完整命令及边界](../outputs/030_gate_training_stability/audit_handoff.md)。')
    docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'];modified=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();c.require(set(modified)==set(docs),'Unexpected history edit')
    paths={p for folder in (c.TASK,c.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for section in ('sources','files','code'):paths.update(c.ROOT/p for p in c.read(c.PREP/'manifest.json')[section])
    paths.update(c.ROOT/p for p in docs+['environment.yml'])
    c.put(c.OUT/'handoff_001.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),tracked_modified=modified,API_calls=0,cost_cny=0,new_closeout_fits=0,independent_audit='pending',no_winner_selected=True,no_automatic_followup=True,sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sorted(paths)}));print('030 handoff frozen',len(paths),'fingerprints; independent audit pending')
if __name__=='__main__':main()
