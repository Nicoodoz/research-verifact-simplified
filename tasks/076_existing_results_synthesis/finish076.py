"""Close 076 with direct invariant checks and current-entry documentation updates."""
import datetime,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/076_existing_results_synthesis';TASK=Path(__file__).parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def write(p,s):Path(p).write_text(s,encoding='utf-8',newline='\n')
def put(p,v):write(p,json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def rewrite(p,fn):
 b=p.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n';s=b.decode('utf-8-sig').replace('\r\n','\n')
 p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))
summary='076零API整理完成：原生重建071–075共1164条逻辑输出，实际264条不同命题、16名评价患者。F4按同ID最早/最晚一对去重，final净+3/+1、false-S均+6；raw共同有效262条净+5/+4，区间均跨0。075存在raw与PriorG方向反转，但动态/批注也有raw损伤，不能归咎单一环节。默认B和Frozen PriorG不变，停止当前示例微调、暂停final pack方法开发，优先论文收束。0元、0拟合，自检PASS；独立审计未执行，不自动077、不提交推送。'
for name,link in [('README.md','outputs/076_existing_results_synthesis/report.md'),('docs/PROJECT_STATUS.md','../outputs/076_existing_results_synthesis/report.md')]:
 def update(t):
  t=t.replace('075结项后','076结项后',1);marker='## 现行摘要（2026-09-24，076结项后）\n\n';assert marker in t
  if '- **076统一整理：**' not in t:t=t.replace(marker,marker+'- **076统一整理：** '+summary+f'[076报告]({link})。\n',1)
  return t.replace('066–072的oracle/诊断与development结果不冒充最终确认','066–076的oracle/诊断与development结果不冒充最终确认',1)
 rewrite(ROOT/name,update)
def agents(t):
 marker='## 现行工作约定（2026-09-24，优先于下方阶段快照）\n\n';assert marker in t
 if '- **076最新：**' not in t:t=t.replace(marker,marker+'- **076最新：** '+summary+'[076报告](outputs/076_existing_results_synthesis/report.md)。\n',1)
 return t.replace('073–075均由用户分别交办，各20元上限；不改`.gitignore`、不使用reserved、不自动076、不提交推送。','073–075均由用户分别交办，各20元上限；076由用户交办完成零API综合。不改`.gitignore`、不使用reserved做新开发、不自动077、不提交推送。',1)
rewrite(ROOT/'AGENTS.md',agents)
def research(t):
 t=t.replace('final pack当前暂停方法开发；071固定医生示例方案是首轮阳性候选，不是默认系统升级。未执行重复不阻止用户另行交办其他有依据的策略比较。','final pack当前暂停方法开发；071首轮示例阳性未得到072–075的明确支持，076已统一核对。F4仅保留简单对照，不继续当前动态/混合/批注微调。未执行重复本身不构成方法失败理由。',1)
 t=t.replace('本原则不自动启动072、不恢复已结项071，也不授权commit/push。','本原则不自动启动后续实验、不恢复已结项任务，也不授权commit/push。',1)
 t=t.replace('详见075报告，不自动启动076。','详见075报告。076由用户交办完成零API统一整理，raw、固定变换及fallback须分开归因，详见[076报告](../outputs/076_existing_results_synthesis/report.md)，不自动启动077。',1)
 return t
rewrite(ROOT/'docs/RESEARCH_EXECUTION.md',research)
rewrite(ROOT/'docs/API_POLICY.md',lambda t:t.replace('075结项后','076结项后',1).replace('073–075各按新任务20元上限执行，详见项目总览。','073–075各按新任务20元上限执行；076为零API整理、费用0元，不改变默认预算或路由，详见项目总览。',1))
for folder in [OUT,TASK]:
 link='report.md' if folder==OUT else '../../outputs/076_existing_results_synthesis/report.md'
 write(folder/'CURRENT_STATUS.md','# 076 当前状态\n\n'+summary+f'\n\n[主报告]({link})\n')
write(OUT/'README.md','# 076 结果入口\n\n'+summary+'\n\n[主报告](report.md) · [数字附录](numeric_appendix.md) · [证据地图](evidence_map.md) · [科学图](stage_decomposition.svg) · [来源指纹](source_manifest.json) · [收尾核验](closure_checks.json)\n')
# Check reconstructed scores independently via multiplicative weights, not common053.
rows=[json.loads(s) for s in (OUT/'unified_predictions.jsonl').read_text().splitlines()];weights=read('fixed_transform.json')['weights'];order=['Not Supported','Not Addressed','Supported'];checked=0
assert len(rows)==1164 and len({x['id'] for x in rows})==264 and len({x['sid'] for x in rows})==16
assert len({(x['stage'],x['id'],x['arm']) for x in rows})==len(rows)
for x in rows:
 if not x['valid']:continue
  # A separate arithmetic formulation checks the deterministic final decision.
 adjusted={k:max(x['scores'][k]/100,1e-6)*weights[k] for k in order}
 assert max(order,key=lambda k:adjusted[k])==x['PriorG'];assert max(order,key=lambda k:x['scores'][k])==x['raw'];checked+=1
pairchecks=0
for stage,pp in read('paired_decomposition.json').items():
 for v in pp.values():
  b={x['id']:x for x in rows if x['stage']==stage and x['arm']==v['base']};a={x['id']:x for x in rows if x['stage']==stage and x['arm']==v['candidate']};assert a.keys()==b.keys()
  common=[i for i in a if a[i]['valid'] and b[i]['valid']];ex=[i for i in a if i not in common]
  def net(ids,key):return sum(int(a[i][key]==a[i]['GT'])-int(b[i][key]==b[i]['GT']) for i in ids)
  assert net(common,'raw')==v['raw_common']['net'];assert net(a,'PriorG')==v['full_final']['net'];assert net(ex,'PriorG')==v['fallback_involved_net'];assert net(common,'PriorG')-net(common,'raw')==v['differential_post_net'];pairchecks+=1
source=read('source_manifest.json');assert all(sha(ROOT/p)==h for p,h in source.items())
history=read('historical_reports.json');assert all(sha(ROOT/x['path'])==x['sha256'] for x in history)
for rel in ['outputs/073_clinical_example_matching','outputs/074_anchor_dynamic_examples','outputs/075_annotated_static_examples']:
 m=json.loads((ROOT/rel/'manifest.json').read_text(encoding='utf-8'))
 assert all(sha(ROOT/p)==h for p,h in m['files'].items())
ignore=(ROOT/'.gitignore').read_bytes();head_ignore=subprocess.check_output(['git','show','HEAD:.gitignore'],cwd=ROOT)
assert ignore.replace(b'\r\n',b'\n')==head_ignore.replace(b'\r\n',b'\n')
assert not subprocess.check_output(['git','diff','--','.gitignore'],cwd=ROOT)
code=[ROOT/'tasks/053_thinking_prior_validation/common053.py']+sorted((ROOT/'src/verifact_research').glob('evaluation*.py'))+sorted((ROOT/'src/verifact_research/evaluation').glob('*.py'))
put(OUT/'analysis_code_sources.json',{p.relative_to(ROOT).as_posix():sha(p) for p in code})
put(OUT/'closure_checks.json',dict(status='PASS',native_reconstruction_checks=read('verification.json')['checks'],separate_multiplicative_decode_checks=checked,pair_decomposition_checks=pairchecks,source_files_unchanged=len(source),historical_report_hashes=len(history),historical_073_075_manifests_unchanged=True,gitignore_content_equal_to_HEAD_ignoring_CRLF=True,gitignore_git_diff_empty=True,gitignore_sha256=sha(ROOT/'.gitignore'),new_API_calls=0,cost_cny=0,new_fits=0,independent_audit='not performed',figure_visual_check='readable, no clipping',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
links=[]
for p in list(OUT.glob('*.md'))+list(TASK.glob('*.md')):
 for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
  if target.startswith(('http:','https:','#')):continue
  target=target.split('#')[0];assert (p.parent/target).exists(),(str(p),target);links.append(target)
docs=['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md']
files=[p for folder in [OUT,TASK] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='manifest.json']
put(OUT/'manifest.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={p.relative_to(ROOT).as_posix():sha(p) for p in files},mutable_docs={p:sha(ROOT/p) for p in docs},verified_local_links=len(links)))
print(json.dumps(dict(status='PASS',valid_decodes=checked,pair_checks=pairchecks,links=len(links),sources_unchanged=len(source)),ensure_ascii=False))
