"""Finalize 077 documentation and hash verification; no experiment is launched."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).parent;OUT=ROOT/'outputs/077_static_example_discrimination'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def write(p,s):Path(p).write_text(s,encoding='utf-8',newline='\n')
def rewrite(p,fn):
 b=p.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n';s=b.decode('utf-8-sig').replace('\r\n','\n');p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))
summary='077零API判别检查完成：B/F4去重共同有效262条、16患者；最早/最晚平均类别对AUC差+0.0040/−0.0044，无全面排序改善。0–20%错误支持率预算下经验混合包络平均PA差+3.75/+4.06个百分点，患者区间跨0；两口径逐患者及任务块留出仍正，但075/80606影响大，LLM方向不稳。仅保留F4低风险工作点的有限验证价值，不升级默认、不再改示例、不重启通用自适应。0元、0拟合，自检PASS，独立审计未执行，不自动078、不提交推送。'
for name,link in [('README.md','outputs/077_static_example_discrimination/report.md'),('docs/PROJECT_STATUS.md','../outputs/077_static_example_discrimination/report.md')]:
 def update(t):
  t=t.replace('076结项后','077结项后',1);marker='## 现行摘要（2026-09-24，077结项后）\n\n';assert marker in t
  if '- **077判别信息：**' not in t:t=t.replace(marker,marker+'- **077判别信息：** '+summary+f'[077报告]({link})。\n',1)
  return t.replace('066–076的oracle/诊断与development结果不冒充最终确认','066–077的oracle/诊断与development结果不冒充最终确认',1)
 rewrite(ROOT/name,update)
def agents(t):
 marker='## 现行工作约定（2026-09-24，优先于下方阶段快照）\n\n';assert marker in t
 if '- **077最新：**' not in t:t=t.replace(marker,marker+'- **077最新：** '+summary+'[077报告](outputs/077_static_example_discrimination/report.md)。\n',1)
 return t.replace('076由用户交办完成零API综合。不改`.gitignore`、不使用reserved做新开发、不自动077、不提交推送。','076/077由用户分别交办完成零API综合与判别诊断。不改`.gitignore`、不使用reserved做新开发、不自动078、不提交推送。',1)
rewrite(ROOT/'AGENTS.md',agents)
def research(t):
 t=t.replace('F4仅保留简单对照，不继续当前动态/混合/批注微调。','077又发现F4的有限低风险经验曲线信号，可保留一次另行交办的简单患者隔离验证价值；不是整体升级或新环境自适应成功。不继续当前动态/混合/批注微调。',1)
 t=t.replace('不自动启动077。当前结果见','077由用户另行交办完成零API分数排序与同风险诊断，详见[077报告](../outputs/077_static_example_discrimination/report.md)，不自动启动078。当前结果见',1)
 return t
rewrite(ROOT/'docs/RESEARCH_EXECUTION.md',research)
rewrite(ROOT/'docs/API_POLICY.md',lambda t:t.replace('076结项后','077结项后',1).replace('076为零API整理、费用0元','076/077均为零API整理/诊断、各费用0元',1))
for folder in [OUT,TASK]:
 link='report.md' if folder==OUT else '../../outputs/077_static_example_discrimination/report.md'
 write(folder/'CURRENT_STATUS.md','# 077 当前状态\n\n'+summary+f'\n\n[主报告]({link})\n')
write(OUT/'README.md','# 077 结果入口\n\n'+summary+'\n\n[主报告](report.md) · [数字附录](numeric_appendix.md) · [同风险曲线](frontiers.svg) · [AUC图](auc_differences.svg) · [论文表述](paper_paragraph.md) · [冻结口径](../../tasks/077_static_example_discrimination/README.md)\n\n复现：用项目环境运行`tasks/077_static_example_discrimination/analyze077.py --output outputs/replays/077_<唯一运行名>`，目标目录须不存在。`verify077.py`检查已生成的正式077曲线；`render077.py`生成表图；`finish077.py`更新当前说明文档并封存。均无API，无模型拟合。\n')
freeze=read(OUT/'analysis_freeze.json');assert sha(TASK/'README.md')==freeze['protocol_sha256'];assert sha(TASK/'analyze077.py')==freeze['analysis_code_sha256']
assert all(sha(ROOT/p)==h for p,h in freeze['sources'].items())
historical=0
for folder in ['073_clinical_example_matching','074_anchor_dynamic_examples','075_annotated_static_examples','076_existing_results_synthesis']:
 m=read(ROOT/'outputs'/folder/'manifest.json')
 for p,h in m['files'].items():assert sha(ROOT/p)==h,p;historical+=1
source=read(ROOT/'outputs/076_existing_results_synthesis/source_manifest.json')
for p,h in source.items():assert sha(ROOT/p)==h,p
assert sha(ROOT/'.gitignore')==read(ROOT/'outputs/076_existing_results_synthesis/closure_checks.json')['gitignore_sha256']
v=read(OUT/'verification.json');fv=read(OUT/'frontier_verification.json');assert v['status']==fv['status']=='PASS'
put(OUT/'closure_checks.json',dict(status='PASS',analysis_checks=v['checks'],separate_frontier_checks=fv['independent_checks'],protocol_and_analysis_code_unchanged_since_freeze=True,historical_manifest_entries_unchanged=historical,historical_source_files_unchanged=len(source),gitignore_unchanged_since076=True,new_API_calls=0,cost_cny=0,new_fits=0,selected_deployment_threshold=None,figure_visual_check='both figures inspected; no clipping or unreadable labels',independent_audit='not performed',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
links=[]
for p in list(OUT.glob('*.md'))+list(TASK.glob('*.md')):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if target.startswith(('https:','http:','#')):continue
  assert (p.parent/target.split('#')[0]).exists(),(str(p),target);links.append(target)
code_sources=[ROOT/'src/verifact_research/evaluation'/x for x in ['__init__.py','core.py','metrics.py']]
put(OUT/'analysis_dependencies.json',{p.relative_to(ROOT).as_posix():sha(p) for p in code_sources})
docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md'];files=[p for folder in [OUT,TASK] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json']
put(OUT/'manifest.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={p.relative_to(ROOT).as_posix():sha(p) for p in files},mutable_docs={p:sha(ROOT/p) for p in docs},verified_local_links=len(links)))
print(json.dumps(dict(status='PASS',historical_manifest_entries=historical,historical_sources=len(source),local_links=len(links),files=len(files)),ensure_ascii=False))
