"""Offline case pointers, navigation and self-check; no model calls."""
import hashlib,json
from pathlib import Path
import common103 as c

def main():
 cases=c.read(c.PRIVATE/'private_case_source_review.json')
 sources={r['id']:r for r in c.lines(c.PRIVATE/'sample240.jsonl')}
 names={'nine_lora':'qwen3.5-9b / lora_label','moe_lora':'qwen3.6-35b-a3b / lora_label'}
 notes=[
 '概括性改善：NS→S救回。窗口存在局部改善描述，但不能仅凭局部原文证明广义总结或模型内部推理。',
 '重复阴性结果及时间对应：NS→S救回。需区分同一次结果被重复记录与独立多次检查。',
 '具体结论与主题相关性：NS→NA救回。reference有相关检查及部分结果，不能将本例描述成完全没有相关主题。',
 '特定事件参与者或内容：NS→NA救回。关键词未命中不等于证明完整EHR不存在；沿医生GT评价。',
 '执行与耐受状态：NS→S误伤。存在操作执行记录，并不完整支持其耐受属性。',
 '药物剂量与因果归因：NS→S误伤。原文有多个可能原因及后续相关用药事件，不能将相关提及等同于完整剂量和因果支持。',
 '概括性恢复：NA→S救回。局部改善与持续问题并存，正确GT不能当成推理过程被验证。',
 '结果与检查类型归属：NS→S救回。原文多种检查并存，保留GT/reference解释限制，不自行作医学重标。',
 '一般状态与具体亚型：NS→S，错误仍错误但新增false-S。准确率转移会漏掉这种风险升级。',
 '实体和检测结果归属：NA→S误伤。一般状态、其他主体的信息不等于目标检测已执行及其结果。',
 '改善与完全消失：NS→S误伤。原文仍有持续异常，另一个过程的消失不能移用到目标状态。',
 '治疗持续与停止：NS→S误伤。原文仍延续目标治疗，其他治疗停用不能替代目标事件。',
 '一般事件与具体内容：NA→S误伤。相关会议或支持信息不完整支持特定场景和内容。',
 '实体出现与事件参与：NA→S误伤。人物角色出现在其他上下文，不证明其参与指定事件。',
 ]
 assert len(cases)==len(notes)==14
 out=['# 103逐例转移与源文核查\n\n这是分析后解释性检查，不参与训练、目标选择、答案替换或规则调整。按冻结的哈希排序规则从指定转移组各选2条，共14条；不是随机总体频率估计。全部转移及患者分布另见final_transitions.jsonl和final_patient_transitions.json。\n\n医生GT针对完整参考EHR，发布reference只是模型输入。局部原文核查不裁决GT，也不把词法窗口当完整证据证明。公开仅给ID、抽象关系类型和源文指针；临床原文保留在私有private_case_source_review.json。字符区间为原reference的Python切片[start:end]，SHA可核对原文。']
 pointers=[]
 for r,note in zip(cases,notes):
  reference=sources[r['id']]['reference'];assert hashlib.sha256(reference.encode()).hexdigest()==r['reference_sha256']
  for s in r['spans']:assert hashlib.sha256(reference[s['start']:s['end']].encode()).hexdigest()==s['sha256']
  item={k:r[k] for k in ['id','sid','panel','GT','before','after','base','candidate','reference_sha256']}
  item['source_spans']=[{k:s[k] for k in ['start','end','sha256']} for s in r['spans']];item['interpretation']=note;pointers.append(item)
  out += [f"\n## {r['id']}\n",f"{r['panel']}；{names[r['candidate']]}；GT={r['GT']}；{r['before']} → {r['after']}。\n\n{note}\n\nreference SHA256：`{r['reference_sha256']}`；核查窗口："+', '.join(f"[{s['start']}:{s['end']}]" for s in r['spans'])+'。']
 (c.OUT/'final_case_analysis.md').write_text('\n'.join(out).rstrip()+'\n',encoding='utf-8');c.put(c.OUT/'final_case_pointers.json',pointers)
 nav='103最终离线分析完成，用户已确认GPU关机：9B与35B各完成512条训练，27B按用户指令停在40条。自然集提升伴随false-S及NS风险恶化，当前纯标签LoRA配方不支持直接全量训练；9B仅保留为较低成本开发候选，27B仍是未解决近邻。35B原生为API参考，没有同ID DeepSeek verifact_ref，不能宣布同Judge超越。新增分析费用0；API累计¥27.518576，最后GPU快照¥30.530395＋磁盘预留¥4，最终平台结算待核。不启动新实验，不升级默认；102继续封存。'
 for rel in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/API_POLICY.md','docs/RUN_ENVIRONMENT.md']:
  p=c.ROOT/rel;raw=p.read_bytes();newline='\r\n' if b'\r\n' in raw else '\n';text=raw.decode('utf-8');parts=text.splitlines();prefix='../' if rel.startswith('docs/') else ''
  for i,line in enumerate(parts):
   if line.startswith('103：'):
    parts[i]=nav+f' [最终报告]({prefix}outputs/103_lora_selection/final_report.md) · [统计附录]({prefix}outputs/103_lora_selection/final_metrics.md)。';break
  if rel=='AGENTS.md':parts=[('- 103训练、推理与最终离线分析已完成，GPU由用户确认关机；当前结论及预算以最终报告为准。未授权新实验或全量训练。' if line.startswith('- 103明确授权') else line) for line in parts]
  if rel=='docs/PROJECT_STATUS.md':
   parts[0]='# 项目现状（2026-10-27，103最终离线分析完成）'
   parts=[('|103微调模型选型|9B与35B训练512及配对分析完成；27B停在40条；用户已关机|自然MCC提升伴随false-S/NS损失，不直接扩大；9B为条件性开发候选，27B未解决；无同Judge verifact_ref确认|' if line.startswith('|103微调模型选型|') else line.replace('[103报告](../outputs/103_lora_selection/report.md)','[103最终报告](../outputs/103_lora_selection/final_report.md)')) for line in parts]
  if rel=='docs/RESEARCH_EXECUTION.md':parts=[line.replace('103已进入GPU执行，最新用户范围以执行报告为准','103已完成关机后的离线分析，最新结论以最终报告为准') for line in parts]
  p.write_bytes((newline.join(parts)+newline).encode('utf-8'))
 p=c.ROOT/'docs/TASK_INDEX.md';raw=p.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';parts=raw.decode('utf-8').splitlines();parts[0]='# 全部任务与当前入口（103最终分析完成；2026-10-27）'
 parts=[('|103_lora_selection|[最终报告](../outputs/103_lora_selection/final_report.md) · [完整指标](../outputs/103_lora_selection/final_metrics.md) · [第一阶段](../outputs/103_lora_selection/report.md)|[执行者自检](../outputs/103_lora_selection/final_selfcheck.json)，非独立审计|9B/35B完成；27B停40条；自然提升伴随风险恶化，不直接全量训练；用户已关机|' if line.startswith('|103_lora_selection|') else line) for line in parts];p.write_bytes((nl.join(parts)+nl).encode('utf-8'))
 progress='''# 103实时进度（最终离线分析完成）

用户已确认GPU关机；监控已停止。本文件现在记录最终状态，不再显示动态计费估算。

- qwen3.6-35b-a3b：512/512条、64/64步，适配器保存并核验回传；本地label_base/lora_label各180/180，native_api复用180/180。
- qwen3.5-9b：512/512条、64/64步，适配器保存并核验回传；native_base/label_base/lora_label各180/180。
- qwen3.8-27b：依用户要求停止，40/512条、5/64步，checkpoint-40留在持久盘，不评价训练效果。
- 自然120：9B LoRA MCC0.5738、PA85.83%、false-S7/24；35B LoRA 0.5176、85.00%、10/24。
- 压力60：9B LoRA MCC0.3182、PA50%、false-S21/60；35B LoRA 0.2624、43.33%、25/60。NS损失明显，当前配方不直接扩大训练。
- 完成1000次患者bootstrap、三类P/R/F1、混淆矩阵、作者分层、逐例与患者转移、源文案例核查、工程敏感性及成本外推；详见[最终报告](final_report.md)。
- API累计按无缓存目录价¥27.518576。最后GPU快照为22:37:40，¥30.530395；磁盘暂留¥4，合计¥34.530395。用户确认其后关机，准确最终账单待平台核对；关机后磁盘保留费用另计。本阶段新增调用/费用0。
- 最终适配器：实例/root/autodl-tmp/verifact103/results/<model>/train/checkpoint-512/；本地.local_models/103_lora_selection/gpu_results/<model>/。基础权重及完整恢复检查点不删除；权重不上传GitHub。
- 最终报告与自检完成后按授权推送两个仓库，发布结果以最终回复中的提交号为准。不会重启GPU或启动新任务。
'''
 (c.OUT/'实时进度.md').write_text(progress.rstrip()+'\n',encoding='utf-8')
 # Independent arithmetic checks, not an independent reviewer.
 a=c.read(c.OUT/'final_analysis.json');checks=0
 for p in a['panels'].values():
  for m in p['metrics'].values():
   cm=m['confusion_matrix'];assert sum(map(sum,cm))==p['N'];assert sum(cm[i][i] for i in range(3))==m['correct'];assert cm[1][0]+cm[2][0]==m['false_S'];checks+=1
 source=c.read(c.OUT/'final_analysis.json')['selfcheck'];assert source['raw_source_sha256']==c.sha(c.OUT/'gpu_predictions_sanitized.jsonl')
 files=['final_analysis.json','final_metrics.md','final_report.md','final_case_analysis.md','final_case_pointers.json','final_transitions.jsonl','final_patient_transitions.json','final_resource_cost_analysis.json','final_risk_intervals.json','final_engineering_sensitivity.json','shutdown_confirmation.json']
 c.put(c.OUT/'final_selfcheck.json',dict(status='executor_checks_passed',independent_audit=False,metric_arithmetic_checks=checks,analysis_checks=source,full_local_label_pairs=360,all_prediction_rows=1080,reference_truncation=False,GT_modified=False,new_paid_API=0,new_GPU=0,user_confirmed_shutdown=True,exact_invoice_unknown=True,source_case_review_count=14,heldout_claim=False,same_Judge_superiority_claim=False,files={f:c.sha(c.OUT/f) for f in files}))
 print('Case explanation, navigation, progress and executor self-check completed')

if __name__=='__main__':main()
