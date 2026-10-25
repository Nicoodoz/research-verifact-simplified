"""Produce traceable result diagnostics and final self-check without new calls."""
import json,csv,collections,sys
from pathlib import Path
from materials073 import ROOT,OUT,read,lines,sha,put,jl
import run073 as r
def report():
 decision=read(OUT/'confirmation_decision.json')
 stages=['pilot']+(['confirmation'] if (OUT/'confirmation_analysis.json').exists() else [])
 analyses={s:read(OUT/f'{s}_analysis.json') for s in stages}
 attempts,answered=r.attempt_state();cost=sum(x['cost_cny'] for x in attempts)
 details=[];gates={};selector_pairs={};validity={}
 for stage,a in analyses.items():
  preds=lines(OUT/f'{stage}_predictions.jsonl');pm={(x['id'],x['arm']):x for x in preds}
  from analyze073 import compare,metric
  blind={x['id']:x for x in lines(OUT/'target_blind.jsonl')}
  gold={x['id']:x for x in lines(OUT/'target_gt.jsonl')}
  ids=sorted({x['id'] for x in preds});rows=[{**blind[k],**gold[k]} for k in ids]
  # Operational fallback is not new Judge learning. Show same-core-valid sensitivity.
  common=[x for x in rows if all(not pm[x['id'],arm]['fallback'] for arm in a['arms'])]
  validity[stage]=dict(n=len(common),excluded_ids=[x['id'] for x in rows if x not in common],final_metrics={arm:metric(common,{k:pm[k,arm]['PriorG'] for k in ids}) for arm in a['arms']},F4_minus_B=compare(common,{k:pm[k,'B']['PriorG'] for k in ids},{k:pm[k,'F4']['PriorG'] for k in ids}))
  if stage=='pilot':
   for arm,base in [('L4','D4'),('M4','D4'),('M4','L4')]:
    selector_pairs[arm+'_minus_'+base]=compare(rows,{k:pm[k,base]['PriorG'] for k in ids},{k:pm[k,arm]['PriorG'] for k in ids})
  for key,pair in a['final_pairs'].items():
   arm,base=key.split('_minus_')
   for kind in ['rescue','harm']:
    for pid in pair[kind+'_ids']:
     x=pm[pid,arm];b=pm[pid,base]
     details.append(dict(stage=stage,comparison=key,kind=kind,id=pid,sid=x['sid'],GT=x['GT'],base_raw=b['raw'],candidate_raw=x['raw'],base_final=b['PriorG'],candidate_final=x['PriorG'],base_fallback=b['fallback'],candidate_fallback=x['fallback'],candidate_raw_correct=x['raw']==x['GT'],same_body=answered[x['request_id']]['job']['body_sha256']==answered[b['request_id']]['job']['body_sha256']))
  if stage=='confirmation':
   for arm in a['arms']:
    if arm=='B':continue
    refs=['B'] if arm=='F4' else ['B','F4'];requirements={}
    for base in refs:
     p=a['final_pairs'][arm+'_minus_'+base]
     requirements[base]=dict(net_ge3=p['net']>=3,MCC_not_lower=a['final_metrics'][arm]['MCC']>=a['final_metrics'][base]['MCC'],falseS_not_increased=p['delta_falseS']<=0,positive_patients_ge3=sum(v>0 for v in p['patient_net'].values())>=3)
    gates[arm]=dict(requirements=requirements,pass_gate=all(v for q in requirements.values() for v in q.values()))
 jl(OUT/'transition_diagnostics.jsonl',details)
 put(OUT/'selector_pairs_pilot.json',selector_pairs)
 put(OUT/'core_valid_sensitivity.json',validity)
 put(OUT/'conclusion.json',dict(stages=stages,confirmation_gates=gates,selected_dynamic=decision['selected_dynamic'],cost_cny=cost,cap_cny=20.,default='B',evidence_level='single-run development comparison; not final independent test',recommendation='limited_development_signal' if any(g['pass_gate'] for g in gates.values()) else 'stop_current_example_matching_version'))
 # Assertions cover frozen files, all arms and physical requests, not just summaries.
 ncheck=0
 for s,a in analyses.items():
  r.check_frozen(s);ncheck+=1
  aliases=lines(OUT/f'{s}_aliases.jsonl');jobs=r.jobs_for(s)
  if s=='confirmation':
   assert sha(OUT/'confirmation_aliases.jsonl')==read(OUT/'confirmation_freeze.json')['aliases_sha256'];ncheck+=1
  assert all(j['request_id'] in answered for j in jobs)
  assert len(jobs)==len({j['body_sha256'] for j in aliases})
  assert len(aliases)==a['n']*len(a['arms']);ncheck+=3
  for j in aliases:
   assert answered[j['request_id']]['job']['body_sha256']==j['body_sha256'];ncheck+=1
  for arm in a['arms']:
   pp=[x for x in lines(OUT/f'{s}_predictions.jsonl') if x['arm']==arm]
   assert len(pp)==a['n'] and sum(x['GT']==x['PriorG'] for x in pp)==a['final_metrics'][arm]['correct'];ncheck+=1
 assert cost<=20 and len(answered)==len({x['job']['body_sha256'] for x in answered.values()});ncheck+=2
 put(OUT/'verification.json',dict(status='PASS',checks=ncheck,preflight_checks=read(OUT/'preflight_checks.json')['n'],synthetic_transport_tests=4,independent_audit='not performed',cost_cny=cost,attempts=len(attempts),answers=len(answered),http_counts=dict(collections.Counter(str(x['http_status']) for x in attempts)),created_utc=r.now()))
 put(OUT/'cost_ledger.json',dict(cap_cny=20.,total_used_or_reserved_cny=cost,price_basis='Aliyun Beijing snapshot0731 peak uncached input3/output9 CNY per million tokens; conservative usage estimate, not reconciled bill',price_url='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',attempts=attempts))
 out=['# 073 临床核验教学示例匹配：实验报告','', '本任务为单轮development策略比较。目标证据、T-S thinking-high及Frozen PriorG保持不变；不代表最终独立测试。','', '## 设计与可识别性','', '072的泛词驱动和回退确实存在。073比较B无示例、F4原静态4例、D4原动态、L4修正词汇+扩库、M4缓存BGE语义+同一扩库。示例库25例（S/NS/NA=12/5/8），每次2S/1NS/1NA，教学24人和评价16人隔离。L4/M4只有表示不同；相对D4/F4的变化含示例库与长度变化，不能单独归因于某一个部件。','', '96条均不在071/072评价命题中，每患者3 human/3 llm，human优先覆盖各类。S/NS/NA=65/16/15；属于刻意丰富困难类别的开发队列，micro成绩不能与072的自然混合队列绝对数直接相比。确认10名患者在历史任务已经暴露，只有本轮策略选择未使用他们的输出。','', '## 主要结果','']
 for s,a in analyses.items():
  out += [f'### {s}：{a["patients"]}人 / {a["n"]}条', '', '| 方法 | 最终正确 | PA | MCC | false-S | raw共同有效正确 |', '|---|---:|---:|---:|---:|---:|']
  for arm in a['arms']:
   m=a['final_metrics'][arm];raw=a['raw_metrics'][arm]
   out.append(f'| {arm} | {m["correct"]}/{a["n"]} | {m["PA"]:.4f} | {m["MCC"]:.4f} | {m["falseS"]} | {raw["correct"]}/{a["raw_common_n"]} |')
  out += ['', '| 配对 | 救回/伤害/净值 | Δfalse-S | ΔMCC [患者95%区间] |', '|---|---:|---:|---|']
  for k,p in a['final_pairs'].items():
   mm=p['paired']['metrics']['mcc']
   out.append(f'| {k} | {p["rescue"]}/{p["harm"]}/{p["net"]:+} | {p["delta_falseS"]:+} | {mm["delta"]:+.4f} [{mm["ci95"][0]:+.4f}, {mm["ci95"][1]:+.4f}] |')
  out += ['',f'GT分布：`{a["GT_counts"]}`；核心无效/fallback：`{a["invalid_by_arm"]}`。', '', '| 作者 | 方法 | 正确 | MCC | false-S |', '|---|---|---:|---:|---:|']
  for author,arms in a['author_metrics'].items():
   for arm,m in arms.items():out.append(f'| {author} | {arm} | {m["correct"]}/{m["n"]} | {m["MCC"]:.4f} | {m["falseS"]} |')
  out+=['','| 方法 | 平均输入token | 平均输出token |','|---|---:|---:|']
  for arm,t in a['tokens_by_arm'].items():out.append(f'| {arm} | {t["prompt_mean"]:.1f} | {t["completion_mean"]:.1f} |')
  out+=['']
 out+=['## 决策与限制','',f'探索后决策：`{decision}`。确认门槛：`{gates}`。','', '当前默认仍为B。若确认门槛通过，也只作为有限开发信号；未通过则停止本版匹配，不继续围绕同批数据搜索。未做成功同体重复不是失败原因，本任务根据观察到的实际比较作决定。','', '匹配质量初查只证明明显泛词退化减少，不是教学效用的医生标注。新增示例保留原完整reference，未生成理由或重判标签。医生GT针对EHR整体，与局部reference的教学契约仍有残余不确定性。L4保留普通数字/否定/时序词，但去除整段去标识化占位符，其中的日期也会去除；不能声称解决所有时间表示。','', '病例级救回/伤害、raw与PriorG关系见transition_diagnostics.jsonl；类别混淆矩阵、患者净收益、bootstrap见各stage_analysis.json。后处理未重新拟合，raw正确数有共同有效分母，最终无效按冻结034 U2回退。','', '## 费用、去重与复现','', f'实际物理尝试{len(attempts)}，成功回答{len(answered)}；累计忙时无缓存估算及未知预留¥{cost:.6f}/20。价格依据：[阿里云官方模型页](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)。该估算未对账，可能高于含优惠实际账单。', '', f'自检PASS：离线{read(OUT/"preflight_checks.json")["n"]}项，执行后{ncheck}项；4项合成传输测试覆盖HTTP0/503恢复、上限拦截和已成功请求跳过，未调用真实API。独立审计未执行。', '', '协议/脚本：[任务README](../../tasks/073_clinical_example_matching/README.md)；freeze.json保存事前协议/代码/材料指纹，confirmation_freeze.json（如有）保存探索后的确认决策；attempts保存每次实际请求及回执。没有使用reserved，没有改.gitignore、原始数据或历史实验，没有提交推送，不自动074。', '', '前处理材料整理遇到历史缓存分散，API前发生三次队列来源补全及一次向量来源补全；未产生收费调用，未按模型成绩修改样本，草稿pool_candidates_incomplete文件保留。']
 (OUT/'report.md').write_text('\n'.join(out)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps(dict(cost=cost,gates=gates,checks=ncheck),ensure_ascii=False))
if __name__=='__main__':report()
