"""Current status sync and final audit handoff, preserving policy/historical bytes."""
from pathlib import Path
import argparse,re,subprocess
import common023 as c
NAV=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md','reviews/README.md','.gitattributes']

def replace(path,old,new):
    p=c.ROOT/path;raw=p.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';old=old.replace('\n',nl).encode();new=new.replace('\n',nl).encode()
    c.require(raw.count(old)==1,'Current navigation marker: '+path);p.write_bytes(raw.replace(old,new,1))
def after(path,prefix,text):
    p=c.ROOT/path;ls=p.read_bytes().splitlines(keepends=True);ix=[i for i,l in enumerate(ls) if l.startswith(prefix.encode())];c.require(len(ix)==1,'Table marker: '+path);i=ix[0];nl=b'\r\n' if ls[i].endswith(b'\r\n') else b'\n';ls.insert(i+1,text.encode()+nl);p.write_bytes(b''.join(ls))
def sync():
    msg='023完成固定λ=2的零API响应/敏感性分析，待独立审计。019/020两轮在约1.946–2.079的标签平台内完全不变，±0.05无改判；较宽近性能区域有重叠，但峰位跨轮漂移，false-S随λ增大。固定λ=2未改，无新winner、不启动024或reserved40。'
    replace('README.md','# Research-VeriFact','# Research-VeriFact\n\n**当前023：** '+msg+'[中文主报告](outputs/023_lambda_boundary_response_analysis/report.md) · [Figure 1](outputs/023_lambda_boundary_response_analysis/figures_001/figure1_performance.pdf) · [交审](outputs/023_lambda_boundary_response_analysis/audit_handoff.md)。')
    replace('AGENTS.md','# 项目背景','# 项目背景\n\n**023当前（2026-09-19）：** '+msg+'[主报告](outputs/023_lambda_boundary_response_analysis/report.md)。023不改变下方API路由或费用政策。')
    replace('docs/PROJECT_STATUS.md','# 项目现状总览','# 项目现状总览\n\n**023当前：** '+msg+'[报告](../outputs/023_lambda_boundary_response_analysis/report.md) · [图表](../outputs/023_lambda_boundary_response_analysis/README.md) · [交审](../outputs/023_lambda_boundary_response_analysis/audit_handoff.md)。')
    replace('reviews/README.md','# 独立审计记录与后续状态','# 独立审计记录与后续状态\n\n**023待独立审计：** 已完成401点与精确切换分析、患者敏感性、两张主图及作者补图，自检通过；0新增API、固定λ=2不变。见[主报告](../outputs/023_lambda_boundary_response_analysis/report.md)与[交接](../outputs/023_lambda_boundary_response_analysis/audit_handoff.md)。尚无023独立审计PASS，不自动开启后续任务或reserved40。')
    after('README.md','| `022_competition_aware_support_calibration`','| `023_lambda_boundary_response_analysis` | 离线响应分析完成；待独立审计；λ=2不变 | [任务](tasks/023_lambda_boundary_response_analysis/CURRENT_STATUS.md) · [报告](outputs/023_lambda_boundary_response_analysis/report.md) · [图](outputs/023_lambda_boundary_response_analysis/README.md) |')
    after('docs/PROJECT_STATUS.md','| 022 |','| 023 | λ=2局部同标签平台及跨批次近性能范围，但峰位/风险并非不变；0API，不重新选λ | [报告](../outputs/023_lambda_boundary_response_analysis/report.md) · [待审](../outputs/023_lambda_boundary_response_analysis/audit_handoff.md) |')
    replace('docs/REPRODUCIBILITY.md','# 当前环境与安全复查入口','# 当前环境与安全复查入口\n\n## 023新增离线复核（尚未独立审计）\n\n`python -B tasks/023_lambda_boundary_response_analysis/verify023.py --output outputs/replays/audit023`\n\n要求新目录、禁止网络；从冻结评分重建401点/精确/患者曲线并比较19个内容文件。历史019–022不变。图重放使用既有research环境Matplotlib3.5.1，命令见[023交审](../outputs/023_lambda_boundary_response_analysis/audit_handoff.md)；不安装新BGE环境、不发API。\n\n以下为既有已审任务的安全入口。')
    p=c.ROOT/'.gitattributes';raw=p.read_bytes();line=b'tasks/023_lambda_boundary_response_analysis/** -text';c.require(line not in raw,'023 attributes already present');nl=b'\r\n' if b'\r\n' in raw else b'\n';p.write_bytes(raw+(b'' if raw.endswith(b'\n') else nl)+line+nl)
    print('023 current navigation synchronized; API_POLICY and.gitignore unchanged.')
def handoff():
    for name in ('preparation_001','analysis_001','description_001','verification_001'):c.check(c.OUT/name)
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();c.require(set(changed)<=set(NAV),'Unexpected historical or policy change')
    c.require((c.ROOT/'docs/API_POLICY.md').read_bytes()==subprocess.check_output(['git','show','HEAD:docs/API_POLICY.md'],cwd=c.ROOT),'API policy changed')
    missing=[]
    for path in list(c.TASK.glob('*.md'))+list(c.OUT.glob('*.md')):
        for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#') and not (path.parent/link.split('#')[0]).resolve().exists():missing.append([str(path),link])
    c.require(not missing,'Broken links: '+c.canonical(missing))
    files={p.relative_to(c.ROOT).as_posix():c.sha(p) for folder in (c.OUT,c.TASK) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update({p:c.sha(c.ROOT/p) for p in NAV+['docs/API_POLICY.md','environment.yml','.gitignore']})
    c.write(c.OUT/'handoff_001.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),files=files,status='completed_pending_independent_audit',tests=dict(task023=10,evaluator002=15),new_API_calls=0,cost_cny=0,fixed_lambda=2,reselected=False,reserved_test_used=False,API_policy_unchanged=True,git_commit_push=False))
    print('Audit handoff saved:',len(files),'files.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--sync',action='store_true');a=p.parse_args();sync() if a.sync else handoff()
