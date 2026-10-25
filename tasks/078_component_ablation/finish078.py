"""Close task078 without committing, pushing or starting task079."""
import re,subprocess
import common078 as c
def rewrite(path,fn):
 b=path.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n';s=b.decode('utf-8-sig').replace('\r\n','\n');path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))
def write(path,s):path.write_text(s,encoding='utf-8',newline='\n')
def main():
 import run078
 f=run078.verify();a,answers=run078.state();v=c.read(c.OUT/'verification.json');assert v['status']=='PASS';assert len(answers)==f['new_jobs'];assert (c.OUT/'report.md').exists()
 st=c.read(c.OUT/'standard_controls_freeze.json')
 for p,h in st['source_sha256'].items():assert c.sha(c.ROOT/p)==h
 t=c.read(c.OUT/'tables.json');main={x['method']:x for x in t['primary_all']};co=c.read(c.OUT/'cost_ledger.json');pairs=c.read(c.OUT/'paired_comparisons.json');f4=next(x for x in pairs['F4_all'] if x['base']=='TS_PriorG' and x['candidate']=='F4_PriorG')
 o,p,m,sv=(main[x] for x in ['Original','TS_PriorG','NS_StdM','NS_StdV'])
 summary=f"078组件消融完成：主384条/24患者，原VeriFact与当前PriorG正确{o['correct']}/{p['correct']}，MCC {o['MCC']:.4f}/{p['MCC']:.4f}；患者外StdM/StdV正确{m['correct']}/{sv['correct']}。192条证据桥接与128条F4次级比较完成，F4＋PriorG较无示例净{f4['net']:+d}、false-S {f4['delta_falseS']:+d}。新增{len(answers)}条HTTP200，费用及未知预留¥{co['estimated_usage_and_unknown_cny']:.6f}/30；Gate采用患者外参数。已暴露development消融，不是新最终测试；自检PASS，独立审计未执行，不自动079、不提交推送。"
 for name,link in [('README.md','outputs/078_component_ablation/report.md'),('docs/PROJECT_STATUS.md','../outputs/078_component_ablation/report.md')]:
  def update(s):
   s=s.replace('077结项后','078结项后',1);marker='## 现行摘要（2026-09-24，078结项后）\n\n';assert marker in s
   if '- **078组件消融：**' not in s:s=s.replace(marker,marker+'- **078组件消融：** '+summary+f'[078报告]({link})。\n',1)
   return s.replace('066–077的oracle/诊断与development结果不冒充最终确认','066–078的oracle/诊断与development结果不冒充最终确认',1)
  rewrite(c.ROOT/name,update)
 def agents(s):
  marker='## 现行工作约定（2026-09-24，优先于下方阶段快照）\n\n';assert marker in s
  if '- **078最新：**' not in s:s=s.replace(marker,marker+'- **078最新：** '+summary+'[078报告](outputs/078_component_ablation/report.md)。\n',1)
  if '- **结果展示：**' not in s:s=s.replace(marker,marker+'- **结果展示：** 主表按“实验配置｜MCC｜PA｜正确数｜错误支持数”展示，先解释配置，固定包含作者原VeriFact在相同ID上的结果；不同队列分表，oracle诊断不冒充实测方法。\n',1)
  return s.replace('076/077由用户分别交办完成零API综合与判别诊断。不改`.gitignore`、不使用reserved做新开发、不自动078、不提交推送。','076/077由用户分别交办完成零API综合与判别诊断；078由用户专项授权30元完成组件消融。不改`.gitignore`、不使用reserved做新开发、不自动079、不提交推送。',1)
 rewrite(c.ROOT/'AGENTS.md',agents)
 rewrite(c.ROOT/'docs/API_POLICY.md',lambda s:s.replace('077结项后','078结项后',1).replace('详见项目总览。','078获用户单任务30元专项上限，累计估算及未知预留¥'+f"{co['estimated_usage_and_unknown_cny']:.6f}"+'，不改变其他新任务默认20元。详见项目总览。',1))
 rewrite(c.ROOT/'docs/RESEARCH_EXECUTION.md',lambda s:s.replace('不自动启动078。当前结果见','078由用户另行交办完成30元上限的组件消融与原作者同队列比较，详见[078报告](../outputs/078_component_ablation/report.md)，不自动启动079。当前结果见',1))
 for folder in [c.OUT,c.TASK]:
  link='report.md' if folder==c.OUT else '../../outputs/078_component_ablation/report.md';write(folder/'CURRENT_STATUS.md','# 078 当前状态\n\n'+summary+f'\n\n[主报告]({link})\n')
 write(c.OUT/'README.md','# 078 结果入口\n\n'+summary+'\n\n[主报告](report.md) · [全部性能表](performance_tables.md) · [成果组件地图](component_inventory.md) · [历史主表](historical_results.md) · [费用](cost_ledger.json) · [冻结协议](../../tasks/078_component_ablation/README.md)\n')
 # All persisted predictions and cohort metrics are internally consistent; preserve historical files.
 checked=0
 for pp in f['source_sha256']:
  assert c.sha(c.ROOT/pp)==f['source_sha256'][pp];checked+=1
 for pp in ['076_existing_results_synthesis','077_static_example_discrimination']:
  mm=c.read(c.ROOT/'outputs'/pp/'manifest.json')
  for path,h in mm['files'].items():assert c.sha(c.ROOT/path)==h;checked+=1
 assert c.sha(c.ROOT/'.gitignore')==c.read(c.ROOT/'outputs/076_existing_results_synthesis/closure_checks.json')['gitignore_sha256']
 assert c.sha(c.TASK/'analyze078.py')==c.read(c.OUT/'GT_join.json')['analysis_code_sha256']
 c.put(c.OUT/'closure_checks.json',dict(status='PASS',source_hash_checks=checked,analysis_checks=v['checks'],synthetic_transport_tests=c.read(c.OUT/'transport_tests.json')['status'],gate_peer_exact_payload_checks=c.read(c.OUT/'source_batch_supplement.json')['gate_peer_exact_claim_reference_checks'],analysis_code_unchanged_since_GT_join=True,real_HTTP200=len(answers),actual_new_fits=0,cost_cny=co['estimated_usage_and_unknown_cny'],cap_cny=30,gitignore_unchanged=True,figure_visual_check='main_results inspected, readable without clipping',independent_audit='not performed',created_utc=c.now()))
 links=[]
 for path in list(c.OUT.glob('*.md'))+list(c.TASK.glob('*.md')):
  for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
   if target.startswith(('https:','http:','#')):continue
   assert (path.parent/target.split('#')[0]).exists(),(path,target);links.append(target)
 files=[p for folder in [c.OUT,c.TASK] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json'];docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md']
 c.put(c.OUT/'manifest.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in files},mutable_docs={p:c.sha(c.ROOT/p) for p in docs},verified_local_links=len(links)))
 print(summary)
if __name__=='__main__':main()
