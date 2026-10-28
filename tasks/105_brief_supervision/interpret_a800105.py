"""Final offline interpretation and executor self-check; preserves historical reports."""
from pathlib import Path
import json,datetime,hashlib,shutil
import common105 as c

def write(p,text):p.write_bytes((text.rstrip()+'\n').encode('utf-8'))

def main():
 private=c.PRIVATE/'a800';e=c.read(c.OUT/'evaluation.json');snap=c.read(private/'latest_snapshot.json');w=private/'evidence/results'
 finish=c.read(private/'evidence/manual_shutdown_needed.json');stamp=datetime.datetime.fromtimestamp(snap['epoch'],datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')
 cost=dict(API_new_cny=0,prior_known_minimum_cny=4.503952316301399,current_rate_cny_per_hour=7.98,current_billing_start_HKT='2026-10-28T15:06:00+08:00',GPU_execution_finish_UTC=finish['utc'],last_remote_observed_HKT=stamp,last_known_total_compute_cny=snap['cost_cny'],shared_unknown_reserve_cny=2,last_known_plus_unknown_reserve_cny=snap['cost_cny']+2,compute_cap_cny=20,cumulative_GPU_known_minutes=(2277.2666959762573+snap['epoch']-1793171160)/60,GPU_cap_minutes=150,automatic_shutdown_executed=False,manual_shutdown_notice_given=True,SSH_later_unreachable=True,user_platform_confirmation_received=False,exact_invoice_pending=True,old_billing_interval_ends_unconfirmed=True,analysis_new_GPU_API_calls=0)
 if (c.OUT/'user_shutdown_confirmation.json').exists():cost.update(user_platform_confirmation_received=True,user_confirmation=c.read(c.OUT/'user_shutdown_confirmation.json'))
 c.put(c.OUT/'a800_cost_status.json',cost)
 for name,dst in [('a800_benchmark.json','a800_benchmark.json'),('gpu_gate.json','a800_gpu_gate.json')]:shutil.copyfile(private/name,c.OUT/dst)
 lead='''**105完整执行结束，短证据监督没有带来额外分类收益，停止当前配方的扩大。** 相对同样本label_only，evidence_brief自然共同390条MCC下降0.1209、PA下降6.67个百分点、净少26条正确，false-S增加2；压力共同94条MCC下降0.2166、净少15条正确，false-S增加7。主要损失是NA被改判NS或S，另有正确S被误报NS。患者bootstrap的两项ΔMCC区间均低于0，但仅覆盖当前已暴露开发患者的固定预测，不代表新医院确认。

两组训练均完成196条×2轮、50步，三组各500条首次回执及两个适配器均已保存回传。未微调基线15条截断、短理由组1条JSON引号错误造成主分析共同有效自然390/400、压力94/100；压力覆盖未达预设95%。纯两训练臂敏感性自然399、压力100仍显示明显负增量，所以不能把失败仅归咎于第三臂格式问题。GPU任务已结束，用户已确认手动关机，程序未关机；精确平台账单和旧区间终点仍待核，费用见a800_cost_status.json。'''
 report=(c.OUT/'final_report.md').read_text(encoding='utf-8');start=report.index('**冻结实验已完成。');end=report.index('\n## 研究问题',start);report=report[:start]+lead+'\n'+report[end:]
 report=report.replace('门槛逐项：`'+json.dumps(e['decision'],ensure_ascii=False)+'`。','''|事前条件|结果|
|---|---|
|自然ΔMCC≥0.02或false-S率下降≥5个百分点|失败：ΔMCC−0.1209，false-S率+2.56个百分点|
|PA下降不超过2个百分点|失败：−6.67个百分点|
|自然false-S率增加不超过2个百分点|失败：+2.56个百分点|
|自然NS召回下降不超过5个百分点|满足：+12个百分点，但区间跨0|
|压力false-S不增加|失败：16→23/94|
|压力NS召回下降不超过5个百分点|满足：58.70%→54.35%|
|相对base_judge不能MCC与false-S同时变差|失败：自然MCC0.3752→0.3671，false-S11→19|
|全部固定请求收齐，两个面板共同有效覆盖≥95%|请求全部收齐；压力94%未达覆盖线|''')
 report+='''

## 结果解释与覆盖敏感性

自然集label_only→evidence_brief：S救回12/误伤24，NS救回6/误伤3，NA救回2/误伤19；净变化分别−12、+3、−17。压力集救回6/误伤21，NS净−2、NA净−13。自然患者净胜/负/平3/10/7，损失最大的单患者净−10；完整患者变化及每条救回、误伤、错误放行转移见paired_transition_summary.json和paired_transitions.jsonl。准确率不变的错→错也可能新增false-S，已单独计数。

自然NS召回40%→52%，但NA召回52.83%→20.75%；压力NS58.70%→54.35%，NA70.83%→43.75%。因此不能把自然NS的局部改善当成少数类整体改善。自然human部分正确163→142、false-S11→13/71；LLM正确151→146、false-S6→6/7。压力human正确59→45、false-S9→15/84；LLM正确2→1、false-S7→8/10。负结果并非只由少量LLM命题造成。

以下是额外离线覆盖敏感性，不替换预设三臂共同有效主表、不新增调用：只比较两种训练方法，自然399条label_only/evidence_brief MCC0.4865/0.3667，Δ−0.1199，95%CI[−0.2306,−0.0228]；压力完整100条为0.4282/0.2036，Δ−0.2247，CI[−0.3919,−0.1011]。压力正确65→49、false-S18→25；负结论保持。详见pair_only_sensitivity.json。

完整自然400条PA界限：base_judge69.25%～71.50%，label_only80.50%，evidence_brief74.00%～74.25%；无效回答不补NA。压力完整100条基线PA界限53%～59%、false-S率9%～15%，标签版PA65%/false-S18%，理由版PA49%/false-S25%。基线15条因384容量截断，按冻结规则保留、不重发；理由组1条为结束正常但JSON引号错误，没有用人工抽出verdict充当有效回执。既未修改输出上限重跑，也未将格式异常直接解释为医学能力失败。

短理由组有效JSON中499条都有非空relation，938/985条引句（95.23%）逐字出现在当前reference；基线为584/1387（42.11%），仅标签组没有理由输出。该机械指标说明更常按指定引用格式作答，不能证明解释与标签对应正确。六条固定hash选择的事后源文案例见final_case_analysis.md：既有明确边界混淆，也有语言歧义和将reference元数据推断为具体事件的问题，不把所有错判都断言为凭空编造。

这次只训练一个固定seed、没有新增同请求重复或重新训练，不能据greedy解码宣称完全稳定。相对label_only自然ΔMCC的患者95%CI[−0.2341,−0.0225]、压力[−0.3865,−0.0865]，在本面板上方向明确，但区间不覆盖历史筛选或重训不确定性。

**停止当前evidence_brief配方的扩量，不追加epoch、提示规则或后处理挽救这500条成绩。** label_only虽然比base_judge有较高MCC/PA，却增加false-S且损失NS召回，也不能因此自动全量训练或升级默认。105证明了该监督构造在当前9B、196条、分段loss和2轮设置下未兑现分类收益；不能扩展成“所有理由监督都无效”。没有同模型DeepSeek verifact_ref同期对照，也没有后续40名患者新评价，不能宣布超过原系统或论文确认成功。

补充离线入口：`sensitivity_a800105.py`生成纯两臂覆盖敏感性；在`write_a800_report105.py`后执行`interpret_a800105.py`生成本解释、源文指针、费用与最终自检。需要本地私有证据，公开克隆不包含可直接训练的临床材料或权重。
'''
 write(c.OUT/'final_report.md',report)
 cases=c.read(private/'source_cases_private.json');explanations=[
 '目标事件未建立，却仍判NS：理由明确承认缺少目标管理事件，仅引用相关对象的既有清单。符合本轮NA→NS错误模式；不能以对象被提及直接替代具体事件被涉及。理由还含引用本身未提供的类别归属，未据此重标GT。',
 '额外要求显式前后轨迹：引用了操作及后续状态，却以未写明此前状态和完整转变过程拒绝原GT。按冻结标签构成S误伤；这里只审查选中引句及理由，不能独立裁定完整EHR的医学结论。',
 '发生时点与到达时状态：原文描述事件在此前发生、到达时已处于该状态；理由将其解释为到达时发生。命题语言也有状态/事件歧义，保留原GT，不把该例当作无争议医学重标依据。',
 '从reference头部元数据推断具体事件：理由使用输入中确实存在的住院终点字段，再将其等同于目标事件。字段真实不证明事件类型和对应关系充分。按固定GT是NA→S风险增加，但不能称为凭空编造引句；也不能据此认定医生标签错误。本轮不改GT、不删例。',
 '区分不同评估对象：理由同时引用对原因及另一结局的不同评估，避免把后一否定直接替代前者，按GT由S救回NS。只是单例可解释收益，不抵消总体损失。',
 '从直接状态记录救回S：引用当前未见活动性问题及状态稳定的原文，与原GT一致。理由中关于材料不完整的附带语句不能作为额外支持依据；正确标签并不保证整段解释每句话都有必要。']
 text=['# 105事后源文案例说明\n\n固定转移组内按SHA256(`105/source_cases/v1/`+ID)各选一条，共6条。只用于解释已完成结果，不参与训练/调参，不代表总体频率。核查对象为原claim、生成短理由、引句及其当前reference邻域，不冒充独立医生审核或完整EHR重标。窗口检查以首次字面出现处为起点，指针另保留全部重现位置；不能据此推断模型关注了哪一次出现。全部原文保留私有source_cases_private.json，公开只给抽象关系说明与指纹。']
 pointers=[]
 for row,explanation in zip(cases,explanations):
  record={k:row[k] for k in ['id','sid','panel','GT','before','after','group','reference_sha256']};record['interpretation']=explanation;record['spans']=[]
  for s in row['spans']:
   positions=[];start=0
   while True:
    found=row['full_reference'].find(s['quote'],start)
    if found<0:break
    positions.append(dict(start=found,end=found+len(s['quote'])));start=found+1
   record['spans'].append(dict(occurrences=positions,quote_sha256=hashlib.sha256(s['quote'].encode()).hexdigest()))
  pointers.append(record)
  text += [f"\n## {row['id']}\n",f"{row['panel']}，GT={row['GT']}；label_only {row['before']} → evidence_brief {row['after']}。\n\n{explanation}\n\nreference SHA256：`{row['reference_sha256']}`；引用位置见final_case_pointers.json。"]
 write(c.OUT/'final_case_analysis.md','\n'.join(text));c.put(c.OUT/'final_case_pointers.json',pointers)
 # Verify arithmetic and input/backup constraints without calling models.
 for part in e['panels'].values():
  for metric in part['metrics'].values():
   cm=metric['confusion_matrix'];assert sum(map(sum,cm))==part['common_valid_N'];assert sum(cm[i][i] for i in range(3))==metric['correct'];assert cm[1][0]+cm[2][0]==metric['false_S']
 for arm in ['label_only','evidence_brief']:
  folder=private/'backup'/arm;receipt=c.read(folder/'critical_backup_verified.json')
  assert c.read(folder/'training_done.json')['updated_lora_B_tensors']==248
  for name,sha in receipt['files'].items():assert c.sha(folder/receipt['remote_final_slot']/name)==sha
 capture=c.read(private/'evidence_backup_verified.json');assert c.sha(private/'a800_evidence.tar.gz')==capture['sha256']
 f=c.read(c.OUT/'preparation_freeze.json');amend=c.read(c.OUT/'nogpu_engineering_amendment.json')
 for name,sha in f['files'].items():assert c.sha(c.ROOT/name)==amend['changed_original_files'].get(name,{}).get('current_sha256',sha)
 c.put(c.OUT/'a800_execution_summary.json',dict(status='GPU_execution_complete',training_steps_per_arm=50,consumed_per_arm=392,first_replies_per_arm=500,adapters_backed_up_and_SHA_verified=True,evidence_archive_SHA256=capture['sha256'],manual_shutdown_notice_given=True,automatic_shutdown=False,clinical_performance_gate_pass=False,coverage_gate_pass=False,API_calls=0))
 files=['final_report.md','final_metrics.md','final_case_analysis.md','final_case_pointers.json','evaluation.json','pair_only_sensitivity.json','predictions_sanitized.jsonl','paired_transitions.jsonl','output_quality.json','a800_resources.json','a800_cost_status.json']
 c.put(c.OUT/'final_selfcheck.json',dict(status='executor_checks_passed',method_pass=False,independent_audit=False,all_fixed_requests_received=True,all1500_input_SHA_checked=True,same_original196_training_order_twice=True,both50step392_consumption_verified=True,all248_LoRA_B_updated_each_arm=True,originalGT_and_reference_unchanged=True,invalid_not_retried_or_fallback=True,all_frozen50_files_unchanged_beyond_recorded_amendment=True,adapter_and_evidence_backup_SHA_verified=True,auto_shutdown=False,paid_API_new=0,limits='Original local CPU suite could not import torch in research-verifact-029; did not install packages. Previous CPU checks, actual GPU path and current offline checks are separate evidence.',files={p:c.sha(c.OUT/p) for p in files}))
 print(c.canonical(dict(finished=True,method_gate=False,last_known_compute_cny=cost['last_known_total_compute_cny'],user_platform_confirmation_received=cost['user_platform_confirmation_received'])))

if __name__=='__main__':main()
