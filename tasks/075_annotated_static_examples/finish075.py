"""Offline closure for the annotated-static-example experiment."""
import ast,collections,subprocess
from common075 import *
import run075 as r
def rewrite(p,fn):
 b=p.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');nl='\r\n' if b'\r\n' in b else '\n';s=b.decode('utf-8-sig').replace('\r\n','\n')
 p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+fn(s).replace('\n',nl).encode('utf-8'))
def main():
 decision=read(OUT/'confirmation_decision.json');stages=['pilot']+(['confirmation'] if (OUT/'confirmation_analysis.json').exists() else [])
 data={s:read(OUT/f'{s}_analysis.json') for s in stages};attempts,answered=r.attempt_state();cost=sum(x['cost_cny'] for x in attempts)
 targets={x['id']:x for x in lines(OUT/'target_blind.jsonl')};transitions=[];boundary={};checks=0
 for stage,a in data.items():
  r.check_frozen(stage);checks+=1
  jobs=r.jobs_for(stage);aliases=lines(OUT/f'{stage}_aliases.jsonl');assert len(jobs)==len({j['body_sha256'] for j in aliases});assert all(j['request_id'] in answered for j in jobs);checks+=2
  if stage=='confirmation':assert sha(OUT/'confirmation_aliases.jsonl')==read(OUT/'confirmation_freeze.json')['aliases_sha256'];checks+=1
  for j in aliases:assert answered[j['request_id']]['job']['body_sha256']==j['body_sha256'];checks+=1
  pred=lines(OUT/f'{stage}_predictions.jsonl');pm={(x['id'],x['arm']):x for x in pred};ids=sorted({x['id'] for x in pred})
  for arm in ['B','F4','R4']:
   assert sum(pm[i,arm]['PriorG']==pm[i,arm]['GT'] for i in ids)==a['final_metrics'][arm]['correct'];checks+=1
  common=[i for i in ids if all(pm[i,k]['raw'] is not None for k in ['B','F4','R4'])]
  boundary[stage]={'raw_common_n':len(common),'NS_NA_swaps':{arm:sum((pm[i,arm]['GT'],pm[i,arm]['raw']) in [('Not Supported','Not Addressed'),('Not Addressed','Not Supported')] for i in common) for arm in ['B','F4','R4']}}
  for key,pair in a['final_pairs'].items():
   arm,base=key.split('_minus_')
   for kind in ['rescue','harm']:
    for i in pair[kind+'_ids']:
     x,b=pm[i,arm],pm[i,base]
     transitions.append(dict(stage=stage,comparison=key,kind=kind,id=i,sid=x['sid'],author=targets[i]['author'],GT=x['GT'],claim=targets[i]['claim'],base_raw=b['raw'],candidate_raw=x['raw'],base_final=b['PriorG'],candidate_final=x['PriorG'],base_fallback=b['fallback'],candidate_fallback=x['fallback'],base_scores=b['scores'],candidate_scores=x['scores'],candidate_raw_correct=x['raw']==x['GT']))
 for rel in ['outputs/073_clinical_example_matching/manifest.json','outputs/074_anchor_dynamic_examples/manifest.json']:
  for p,h in read(ROOT/rel)['files'].items():assert sha(ROOT/p)==h,p;checks+=1
 for p in TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));checks+=1
 assert cost<=20 and len(answered)==len({x['job']['body_sha256'] for x in answered.values()}) and not (OUT/'run.lock').exists();checks+=3
 gate={}
 if 'confirmation' in data:
  a=data['confirmation'];m=a['final_metrics'];v=a['core_valid_final_metrics'];raw=a['raw_metrics']
  for base,minimum in [('B',3),('F4',2)]:
   p=a['final_pairs']['R4_minus_'+base]
   gate[base]=dict(final_net_met=p['net']>=minimum,MCC_not_lower=m['R4']['MCC']>=m[base]['MCC'],falseS_not_higher=m['R4']['falseS']<=m[base]['falseS'],core_valid_positive=v['R4']['correct']>v[base]['correct'])
  gate['raw']=dict(increment_F4_ge2=raw['R4']['correct']>=raw['F4']['correct']+2,not_below_B=raw['R4']['correct']>=raw['B']['correct'])
  gate['patients']=dict(at_least_three_positive=sum(v>0 for v in a['final_pairs']['R4_minus_F4']['patient_net'].values())>=3)
 signal=bool(gate) and all(v for d in gate.values() for v in d.values())
 parsed=collections.Counter(x['parsed']['status'] for x in answered.values());valid=sum(parsed[k] for k in r.c53.VALID)
 put(OUT/'conclusion.json',dict(status='completed',stages=stages,evidence_level='single-run development; not independent final test',pilot_decision=decision,confirmation_gate=gate,limited_positive_signal=signal,recommendation='retain_annotation_candidate_for_development' if signal else 'stop_current_annotation_version',default='B',cap_cny=20,cost_cny=cost))
 jl(OUT/'transition_diagnostics.jsonl',transitions);put(OUT/'boundary_diagnostics.json',boundary)
 put(OUT/'cost_ledger.json',dict(total_used_or_reserved_cny=cost,cap_cny=20,price_input=3,price_output=9,unit='CNY per million tokens, peak uncached conservative usage estimate',price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',attempts=attempts))
 put(OUT/'verification.json',dict(status='PASS',checks=checks,preflight=read(OUT/'preflight_checks.json'),synthetic_transport_tests=4,HTTP_counts=dict(collections.Counter(str(x['http_status']) for x in attempts)),parsed_status=dict(parsed),historical073_074_unchanged=True,independent_audit='not performed',created_utc=now()))
 p=data['pilot'];counts='/'.join(str(p['final_metrics'][k]['correct']) for k in ['B','F4','R4']);rawcounts='/'.join(str(p['raw_metrics'][k]['correct']) for k in ['B','F4','R4'])
 summary=f'075固定四例批注已完成：36条探索B/F4/R4最终正确{counts}，raw共同有效{p["raw_common_n"]}条正确{rawcounts}；'
 if 'confirmation' not in data:summary+='未通过探索条件，未执行60条确认，停止本版本。' if decision['reason']=='annotation_screen_failed' else '因预算预估停止，尚无确认结论。'
 else:
  a=data['confirmation'];c='/'.join(str(a['final_metrics'][k]['correct']) for k in ['B','F4','R4']);summary+=f'另60条确认最终正确{c}；'+('保留有限开发信号。' if signal else '未达确认条件，停止本版本。')
 summary+=f'默认B不变，累计估算¥{cost:.6f}/20，{len(answered)}个HTTP200、{valid}核心有效；自检PASS，独立审计未执行，不自动076、不提交推送。'
 out=['# 075 固定四例的证据批注','', '**'+summary+'**','', '## 实验设计','', 'B无示例；F4沿用原071的4例；R4在完全相同的F4系统消息后追加4段批注。原例子的命题、EHR、标签、顺序与目标证据、模型、输出要求和Frozen PriorG均不变。批注约495个英文词、4213字符，含5处已逐条核对的引句；这是研究者/Codex基于现有reference编写的教学说明，不是医生原始理由，不是新增GT。没有手填label_scores。','', '[实际批注及原文编号](annotations_review.md)覆盖：直接对应、未证实的特定因果、忠实保留原文限定、未记录的具体测量。这里可以核对的是例子的证据关系；模型能否从中学到可迁移规则由实验检验。未设计等长普通说明控制，若有增益也只能归于批注包整体，不直接声称内部推理机制。','', '预先准备96条不在071–074准备清单中的新命题，仍来自已暴露的16名development患者，6人36条探索/10人60条确认。教学4人完全隔离。各作者优先覆盖S/NS/NA，属于类别丰富的诊断队列；human/llm分别报告，不与历史任务的绝对分数直接相减。若探索停止，60条确认只准备输入、没有新模型输出。','', '## 分阶段结果','']
 for stage,a in data.items():
  out += [f'### {stage}：{a["patients"]}人、{a["n"]}条','', '|方法|最终正确|MCC|错误支持|raw正确|共同核心有效最终正确|','|---|---:|---:|---:|---:|---:|']
  for arm in ['B','F4','R4']:
   m=a['final_metrics'][arm];ra=a['raw_metrics'][arm];v=a['core_valid_final_metrics'][arm]
   out.append(f'|{arm}|{m["correct"]}/{a["n"]}|{m["MCC"]:.4f}|{m["falseS"]}|{ra["correct"]}/{a["raw_common_n"]}|{v["correct"]}/{a["core_valid_n"]}|')
  out+=['','|比较|救回/伤害/净值|Δ错误支持|ΔMCC及患者95%区间|','|---|---:|---:|---|']
  for k in ['F4_minus_B','R4_minus_B','R4_minus_F4']:
   q=a['final_pairs'][k];mm=q['paired']['metrics']['mcc'];lo,hi=mm['ci95'];out.append(f'|{k}|{q["rescue"]}/{q["harm"]}/{q["net"]:+}|{q["delta_falseS"]:+}|{mm["delta"]:+.4f} [{lo:+.4f}, {hi:+.4f}]|')
  out+=['',f'GT：`{a["GT_counts"]}`；核心无效/fallback：`{a["invalid_by_arm"]}`。',f'raw中NS↔NA混淆数：`{boundary[stage]["NS_NA_swaps"]}`，分母为共同有效{a["raw_common_n"]}条。','', '|作者|方法|最终正确|MCC|错误支持|','|---|---|---:|---:|---:|']
  for author,arms in a['author_metrics'].items():
   for arm,m in arms.items():out.append(f'|{author}|{arm}|{m["correct"]}/{m["n"]}|{m["MCC"]:.4f}|{m["falseS"]}|')
  out+=['','|方法|平均输入token|平均输出token|每次估算元|','|---|---:|---:|---:|']
  for arm,t in a['tokens_by_arm'].items():out.append(f'|{arm}|{t["prompt_mean"]:.1f}|{t["completion_mean"]:.1f}|{(t["prompt_mean"]*3+t["completion_mean"]*9)/1e6:.5f}|')
  out+=['']
 out+=['## 研究决策与边界','', f'探索后决策：`{decision["decision"]}`，原因`{decision["reason"]}`。确认信号条件：`{gate}`。批注没有在看到075结果后改写，没有搜索替代版本。', '', '是否值得继续由完整配对结果决定；未重复成功调用只限定证据等级，不当作方法失败理由。raw、最终标签和fallback分别记录，不能把历史U2回退或PriorG改判全部叫作新推理救回。若两层方向不同，仅报告兼容性，不在本任务重新拟合后处理。','', '医生GT针对EHR整体，而解释针对当前提供的reference；4例已进行证据核对，但不据此保证所有目标病例的证据包都足以复现医生标签。reason、checks及病例解释均不是模型内部因果证明。NS/NA的具体边界不能由一例无条件推广。','', '## 执行与复现','', f'物理尝试{len(attempts)}、HTTP200 {len(answered)}、核心有效{valid}，累计估算及未知预留¥{cost:.6f}/20；按[阿里云官方0731北京忙时价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)输入3/输出9元每百万token保守计算，未核对折扣账单。0 embedding调用，成功同体不重复。', '', f'预检{read(OUT/"preflight_checks.json")["checks"]}项PASS，合成传输测试4项PASS，执行后{checks}项PASS；独立审计未执行。原始数据、073/074及更早工件、.gitignore和密钥配置未修改。不提交推送、不自动076。','', '[事前协议](../../tasks/075_annotated_static_examples/README.md) · [批注](annotations_review.md) · [逐例变化](transition_diagnostics.jsonl) · [费用](cost_ledger.json) · [自检](verification.json)']
 (OUT/'report.md').write_text('\n'.join(out)+'\n',encoding='utf-8',newline='\n')
 for folder in [OUT,TASK]:
  link='report.md' if folder==OUT else '../../outputs/075_annotated_static_examples/report.md';(folder/'CURRENT_STATUS.md').write_text('# 075 当前状态\n\n'+summary+f'\n\n[完整报告]({link})\n',encoding='utf-8',newline='\n')
 (OUT/'README.md').write_text('# 075 结果入口\n\n'+summary+'\n\n[正式报告](report.md) · [批注稿](annotations_review.md) · [事前协议](../../tasks/075_annotated_static_examples/README.md)\n',encoding='utf-8',newline='\n')
 for name,link in [('README.md','outputs/075_annotated_static_examples/report.md'),('docs/PROJECT_STATUS.md','../outputs/075_annotated_static_examples/report.md')]:
  def update(t):
   t=t.replace('074结项后','075结项后',1);marker='## 现行摘要（2026-09-24，075结项后）\n\n';assert marker in t
   return t.replace(marker,marker+'- **075静态批注：** '+summary+f'[075报告]({link})。\n',1)
  rewrite(ROOT/name,update)
 marker='## 现行工作约定（2026-09-24，优先于下方阶段快照）\n\n'
 rewrite(ROOT/'AGENTS.md',lambda t:t.replace(marker,marker+'- **075最新：** '+summary+'[075报告](outputs/075_annotated_static_examples/report.md)。\n',1).replace('073和074均由用户分别交办，各20元上限；不改`.gitignore`、不使用reserved、不自动075、不提交推送。','073–075均由用户分别交办，各20元上限；不改`.gitignore`、不使用reserved、不自动076、不提交推送。',1))
 rewrite(ROOT/'docs/RESEARCH_EXECUTION.md',lambda t:t.replace('详见074报告，不自动启动075。','详见074报告。075由用户另行交办完成固定四例的证据批注比较，详见075报告，不自动启动076。'))
 rewrite(ROOT/'docs/API_POLICY.md',lambda t:t.replace('074结项后','075结项后',1).replace('071–074均不自动升级默认Judge；073/074各按新任务20元上限执行','071–075均不自动升级默认Judge；073–075各按新任务20元上限执行',1))
 files=[p for folder in [OUT,TASK] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 put(OUT/'manifest.json',dict(created_utc=now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),files={p.relative_to(ROOT).as_posix():sha(p) for p in files},mutable_docs={n:sha(ROOT/n) for n in ['README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md']}))
 print(summary)
if __name__=='__main__':main()
