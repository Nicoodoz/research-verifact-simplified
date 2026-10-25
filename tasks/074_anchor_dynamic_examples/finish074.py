"""Offline result interpretation, artifact checks and mutable project navigation."""
import collections,json,subprocess,ast
from common074 import *
import run074 as r
from analyze074 import metric,compare
def rewrite(path,fn):
 b=path.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n'
 s=b.decode('utf-8-sig').replace('\r\n','\n');new=fn(s).replace('\n',nl).encode('utf-8');path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+new)
def main():
 decision=read(OUT/'confirmation_decision.json');stages=['pilot']+(['confirmation'] if (OUT/'confirmation_analysis.json').exists() else [])
 results={s:read(OUT/f'{s}_analysis.json') for s in stages};attempts,answered=r.attempt_state();cost=sum(x['cost_cny'] for x in attempts)
 blind={x['id']:x for x in lines(OUT/'target_blind.jsonl')};gold={x['id']:x for x in lines(OUT/'target_gt.jsonl')};sels={x['id']:x for x in lines(OUT/'selections.jsonl')};pool={x['proposition_id']:x for x in lines(OUT/'example_pool.jsonl')}
 transitions=[];diagnostic={};checks=0
 for stage,a in results.items():
  r.check_frozen(stage);checks+=1
  jobs=r.jobs_for(stage);aliases=lines(OUT/f'{stage}_aliases.jsonl');assert len(jobs)==len({j['body_sha256'] for j in aliases});assert all(j['request_id'] in answered for j in jobs);checks+=2
  if stage=='confirmation':assert sha(OUT/'confirmation_aliases.jsonl')==read(OUT/'confirmation_freeze.json')['aliases_sha256'];checks+=1
  for j in aliases:assert answered[j['request_id']]['job']['body_sha256']==j['body_sha256'];checks+=1
  pred=lines(OUT/f'{stage}_predictions.jsonl');pm={(x['id'],x['arm']):x for x in pred};ids=sorted({x['id'] for x in pred});rows=[{**blind[i],**gold[i]} for i in ids]
  for arm in a['arms']:
   assert sum(pm[i,arm]['PriorG']==gold[i]['GT'] for i in ids)==a['final_metrics'][arm]['correct'];checks+=1
  for key,pair in a['final_pairs'].items():
   arm,base=key.split('_minus_')
   for kind in ['rescue','harm']:
    for i in pair[kind+'_ids']:
     x,b=pm[i,arm],pm[i,base]
     transitions.append(dict(stage=stage,comparison=key,kind=kind,id=i,sid=x['sid'],author=blind[i]['author'],GT=x['GT'],claim=blind[i]['claim'],base_raw=b['raw'],candidate_raw=x['raw'],base_final=b['PriorG'],candidate_final=x['PriorG'],base_fallback=b['fallback'],candidate_fallback=x['fallback'],candidate_raw_correct=x['raw']==x['GT'],base_scores=b['scores'],candidate_scores=x['scores']))
  # Descriptive only: same added-label composition and explicit relation coverage.
  subgroups={'matched_added_label_multiset':[x for x in rows if sorted(sels[x['id']]['dynamic_labels'])==sorted(pool[i]['physician_label'] for i in sels[x['id']]['static_ids'])], 'explicit_relation':[x for x in rows if sels[x['id']]['target_tags']], 'semantic_only':[x for x in rows if not sels[x['id']]['target_tags']]}
  diagnostic[stage]={}
  for name,subset in subgroups.items():
   if len({x['sid'] for x in subset})>=2:
    diagnostic[stage][name]=dict(n=len(subset),pair=compare(subset,{i:pm[i,'F6']['PriorG'] for i in ids},{i:pm[i,'H6']['PriorG'] for i in ids}))
   else:
    diagnostic[stage][name]=dict(n=len(subset),patients=len({x['sid'] for x in subset}),pair=None,reason='fewer_than_two_patients_no_cluster_CI',correct_F6=sum(pm[x['id'],'F6']['PriorG']==x['GT'] for x in subset),correct_H6=sum(pm[x['id'],'H6']['PriorG']==x['GT'] for x in subset))
 status=collections.Counter(x['parsed']['status'] for x in answered.values());valid=sum(status[k] for k in r.c53.VALID)
 assert cost<=20 and len(answered)==len({x['job']['body_sha256'] for x in answered.values()});checks+=2
 old=read(ROOT/'outputs/073_clinical_example_matching/manifest.json')
 for rel,h in old['files'].items():assert sha(ROOT/rel)==h,rel;checks+=1
 for p in TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));checks+=1
 assert not (OUT/'run.lock').exists();checks+=1
 confirmation_gate={}
 if 'confirmation' in results:
  a=results['confirmation'];m=a['final_metrics'];v=a['core_valid_final_metrics']
  for base in ['B','F4','F6']:
   p=a['final_pairs']['H6_minus_'+base];patient=p['patient_net']
   confirmation_gate[base]=dict(net_ge3=p['net']>=3,MCC_not_lower=m['H6']['MCC']>=m[base]['MCC'],falseS_not_higher=m['H6']['falseS']<=m[base]['falseS'],core_valid_positive=v['H6']['correct']>v[base]['correct'])
  p=a['final_pairs']['H6_minus_F6'];confirmation_gate['distribution']=dict(positive_patients_ge3=sum(v>0 for v in p['patient_net'].values())>=3,net_without_best_patient_positive=p['net']-max(p['patient_net'].values())>0)
 signal=bool(confirmation_gate) and all(v for d in confirmation_gate.values() for v in d.values())
 conclusion=dict(status='completed',evidence_level='single-run development; no independent final test',pilot_decision=decision,confirmation_gate=confirmation_gate,limited_positive_signal=signal,recommendation='retain_for_further_development' if signal else 'stop_current_hybrid_version',default='B',cost_cny=cost,cap_cny=20,stages=stages)
 put(OUT/'conclusion.json',conclusion);jl(OUT/'transition_diagnostics.jsonl',transitions);put(OUT/'mechanism_subgroups.json',diagnostic)
 put(OUT/'cost_ledger.json',dict(total_used_or_reserved_cny=cost,cap_cny=20,price_input=3,price_output=9,unit='CNY per million tokens, peak uncached conservative estimate',price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',attempts=attempts))
 put(OUT/'verification.json',dict(status='PASS',checks=checks,preflight=read(OUT/'preflight_checks.json'),transport_synthetic_tests=4,HTTP_counts=dict(collections.Counter(str(x['http_status']) for x in attempts)),core_status=dict(status),historical073_manifest_unchanged=True,independent_audit='not performed',created_utc=now()))
 p=results['pilot'];counts='/'.join(str(p['final_metrics'][k]['correct']) for k in ['B','F4','F6','H6'])
 summary=f'074固定锚点＋动态补例已完成：36条新命题探索B/F4/F6/H6最终正确{counts}；'
 if 'confirmation' not in results:summary+='混合方案未进入确认，停止本版本。' if decision['reason']=='hybrid_screen_failed' else '探索后因预算预估停止，尚无确认结论。'
 else:
  a=results['confirmation'];cc='/'.join(str(a['final_metrics'][k]['correct']) for k in ['B','F4','F6','H6']);summary+=f'另60条确认正确{cc}；'+('保留有限开发信号。' if signal else '未达确认门槛，停止本版本。')
 summary+=f'默认B不变，累计估算¥{cost:.6f}/20，{len(answered)}个HTTP200、{valid}核心有效；未重复成功同体、未用reserved、未改.gitignore，自检PASS，独立审计未执行，不自动075、不提交推送。'
 out=['# 074 固定代表例子＋动态补充例子','', '**'+summary+'**','', '## 实验设置与识别边界','', 'B无示例；F4原固定4例；F6固定4例＋固定2例；H6固定4例＋动态2例。目标证据、Judge、评分结构和Frozen PriorG相同，固定4例的文本逐字保留。新增2例长度在固定补例的±10%内。匹配只读目标claim，BGE全部缓存；动态与静态新增例的标签组成未完全匹配，因此本实验比较完整策略，不能单独证明关系匹配机制。', '', '教学库沿用073已筛查25例，原医生标签及reference不变。96条命题均不在071–073评价ID中，同16名development患者，6人36条探索/10人60条确认。各作者优先覆盖三类，属于有意丰富困难类别的开发诊断，分别报告human/llm，不能把micro成绩当自然分布或未接触最终测试。','', '## 分阶段结果','']
 for stage,a in results.items():
  out += [f'### {stage}：{a["patients"]}人、{a["n"]}条','', '|方法|最终正确|MCC|错误支持|raw正确|共同核心有效最终正确|','|---|---:|---:|---:|---:|---:|']
  for arm in ['B','F4','F6','H6']:
   m=a['final_metrics'][arm];ra=a['raw_metrics'][arm];va=a['core_valid_final_metrics'][arm]
   out.append(f'|{arm}|{m["correct"]}/{a["n"]}|{m["MCC"]:.4f}|{m["falseS"]}|{ra["correct"]}/{a["raw_common_n"]}|{va["correct"]}/{a["core_valid_n"]}|')
  out+=['','|比较|救回/伤害/净值|Δ错误支持|ΔMCC及患者95%区间|','|---|---:|---:|---|']
  for k in ['F4_minus_B','F6_minus_F4','H6_minus_B','H6_minus_F4','H6_minus_F6']:
   q=a['final_pairs'][k];mm=q['paired']['metrics']['mcc'];lo,hi=mm['ci95']
   out.append(f'|{k}|{q["rescue"]}/{q["harm"]}/{q["net"]:+}|{q["delta_falseS"]:+}|{mm["delta"]:+.4f} [{lo:+.4f}, {hi:+.4f}]|')
  out+=['',f'GT：`{a["GT_counts"]}`；核心无效/fallback：`{a["invalid_by_arm"]}`。','', '|作者|方法|最终正确|MCC|错误支持|','|---|---|---:|---:|---:|']
  for author,arms in a['author_metrics'].items():
   for arm,m in arms.items():out.append(f'|{author}|{arm}|{m["correct"]}/{m["n"]}|{m["MCC"]:.4f}|{m["falseS"]}|')
  out+=['','|方法|平均输入token|平均输出token|每逻辑请求估算元|','|---|---:|---:|---:|']
  for arm,t in a['tokens_by_arm'].items():out.append(f'|{arm}|{t["prompt_mean"]:.1f}|{t["completion_mean"]:.1f}|{(t["prompt_mean"]*3+t["completion_mean"]*9)/1e6:.5f}|')
  out+=['']
 out+=['## 选择诊断与限制','', '固定额外例由教学库的两中心覆盖选出，标签为NS/NA；这只是教学库内代表性，不是医生认定的最佳教学范例。动态附加例标签组成经常不同：同标签组成的子组分析见mechanism_subgroups.json，仅作描述、不据其改选方法。','', '96条中40条触发显式关系规则，56条没有触发，后者实际依赖语义匹配。临床缩写HD（住院第几日）及缺少单位的部分数值未被当前规则识别；有限教学库也缺少部分主题（如INR）。不能说每个动态例子都已达到临床上“更契合”，更不能把负结果推广为所有混合教学策略无效。调用开始后的选择器与库未改。','', '唯一候选是否继续由事前冻结规则决定；fallback收益与共同核心有效结果分开，不借截断回退作为唯一正信号。不默认重复成功实验，普通故障有限恢复。本任务的否定/肯定结论基于观察到的配对表现，不基于是否进行了稳定性重复。','', '全部病例变化、raw与PriorG/fallback关系见transition_diagnostics.jsonl；类别混淆、患者方向、raw配对及统一bootstrap见各stage_analysis.json。与071–073的队列构成不同，禁止跨任务绝对分数直接相减。','', '## 费用、执行与复现','', f'实际尝试{len(attempts)}，HTTP200 {len(answered)}，核心有效{valid}；累计费用及未知预留估算¥{cost:.6f}/20，按[官方0731北京忙时价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)输入3/输出9元每百万token保守估算，未核对优惠账单。没有新embedding调用。', '', f'离线预检{read(OUT/"preflight_checks.json")["checks"]}项PASS，合成传输4项PASS，执行后{checks}项PASS；自检不等于方法成功或独立审计。未改原始数据、073及更早冻结结果、.gitignore或密钥配置；未提交推送，不自动075。','', '[事前协议](../../tasks/074_anchor_dynamic_examples/README.md) · [探索后决策](confirmation_decision.json) · [结论](conclusion.json) · [费用账本](cost_ledger.json) · [自检](verification.json)']
 report='\n'.join(out)+'\n'
 report=report.replace('96条命题均不在071–073评价ID中','预先准备的96条命题均不在071–073评价ID中')
 report=report.replace('不能把micro成绩当自然分布或未接触最终测试。','不能把micro成绩当自然分布或未接触最终测试。若探索停止，60条确认仅准备输入而未执行，实际评价分母以分阶段结果为准。')
 report=report.replace('有限教学库也缺少部分主题（如INR）。','有限教学库也缺少部分主题（如INR）。关系标签只描述claim中的语言线索，未判断claim与目标reference之间的实际支持/矛盾关系，例如无法仅凭claim知道证据是否只记载计划而未记载实施。')
 (OUT/'report.md').write_text(report,encoding='utf-8',newline='\n')
 for folder in [OUT,TASK]:
  link='report.md' if folder==OUT else '../../outputs/074_anchor_dynamic_examples/report.md'
  (folder/'CURRENT_STATUS.md').write_text('# 074 当前状态\n\n'+summary+f'\n\n[报告]({link})\n',encoding='utf-8',newline='\n')
 (OUT/'README.md').write_text('# 074 结果入口\n\n'+summary+'\n\n[正式报告](report.md) · [事前协议](../../tasks/074_anchor_dynamic_examples/README.md) · [逐例变化](transition_diagnostics.jsonl) · [费用](cost_ledger.json)\n',encoding='utf-8',newline='\n')
 for name,link in [('README.md','outputs/074_anchor_dynamic_examples/report.md'),('docs/PROJECT_STATUS.md','../outputs/074_anchor_dynamic_examples/report.md')]:
  def update(t):
   t=t.replace('073结项后','074结项后',1);marker='## 现行摘要（2026-09-24，074结项后）\n\n';assert marker in t
   return t.replace(marker,marker+'- **074混合教学示例：** '+summary+f'[074报告]({link})。\n',1)
  rewrite(ROOT/name,update)
 marker='## 现行工作约定（2026-09-24，优先于下方阶段快照）\n\n'
 rewrite(ROOT/'AGENTS.md',lambda t:t.replace(marker,marker+'- **074最新：** '+summary+'[074报告](outputs/074_anchor_dynamic_examples/report.md)。\n',1).replace('073由用户新交办，20元上限；不改`.gitignore`、不使用reserved、不自动074、不提交推送。','073和074均由用户分别交办，各20元上限；不改`.gitignore`、不使用reserved、不自动075、不提交推送。',1))
 rewrite(ROOT/'docs/RESEARCH_EXECUTION.md',lambda t:t.replace('结果及静态确认见073报告，不自动启动074。','结果及静态确认见073报告。074由用户另行交办完成固定锚点＋动态补例比较，详见074报告，不自动启动075。'))
 rewrite(ROOT/'docs/API_POLICY.md',lambda t:t.replace('## 现行路由与恢复原则（2026-09-23，072结项后）','## 现行路由与恢复原则（2026-09-24，074结项后）',1).replace('071首轮阳性及072开发结果均不自动升级默认Judge。','071–074均不自动升级默认Judge；073/074各按新任务20元上限执行，详见项目总览。',1))
 files=[p for directory in [OUT,TASK] for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 put(OUT/'manifest.json',dict(created_utc=now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={p.relative_to(ROOT).as_posix():sha(p) for p in files},mutable_docs={n:sha(ROOT/n) for n in ['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md']}))
 print(summary)
if __name__=='__main__':main()
