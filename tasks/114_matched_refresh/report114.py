"""Render actual results and returned-state checks after GPU work has ended."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/114_matched_refresh';O=R/'outputs/114_matched_refresh';L=c.LABELS
def pct(x):return '—' if x is None else f'{100*x:.2f}%'
def date(t):return datetime.fromtimestamp(t,timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
def main():
 d=c.read(O/'comparison.json');session=c.read(P/'session.json');returned=c.read(P/'return_checkpoint.json');key=c.read(P/'return_key.json');done=c.read(P/'evidence/results/gpu_done.json');train=P/'evidence/results/train';pointer=c.read(train/'resume.json');complete=c.read(train/pointer['slot']/'checkpoint_complete.json')
 assert pointer['step']==50 and pointer['consumed']==392 and complete['step']==50
 assert c.sha(train/pointer['slot']/'checkpoint_complete.json')==pointer['complete_sha256']
 checks={name:c.sha(train/pointer['slot']/name)==wanted for name,wanted in complete['files'].items()};assert all(checks.values())
 steps=c.rows(train/'steps.jsonl');assert [r['step'] for r in steps]==list(range(1,51)) and [r['loss_divisor'] for r in steps if r['loss_divisor']!=8]==[4,4]
 ev=c.read(P/'evidence/results/evaluation_done.json');assert ev['N']==500
 end=max(returned['returned_epoch'],key['returned_epoch'])
 cost=dict(task=114,start_beijing=date(session['start_epoch']),task_end_beijing=date(end),GPU_done_beijing=date(done['epoch']),key_return_beijing=date(key['returned_epoch']),final_checkpoint_return_beijing=date(returned['returned_epoch']),task_wall_minutes=(end-session['start_epoch'])/60,hourly_CNY=session['rate'],estimated_GPU_CNY=(end-session['start_epoch'])*session['rate']/3600,cap_CNY=3,API_CNY=0,platform_exact_bill_confirmed=False,no_shutdown=True,instance_power_state='left_running_per_user_policy',post_task_user_idle_excluded=True,historical_ledgers_unchanged=True,train_logged_seconds=sum(r['seconds'] for r in steps),eval_seconds=ev['seconds'],checkpoint_return_parallel_with_evaluation=returned.get('parallel_with_official_evaluation',False))
 assert cost['estimated_GPU_CNY']<=3
 c.put(O/'cost_status.json',cost);c.put(O/'final_selfcheck.json',dict(training50steps392=True,short_tails_normalized4=True,complete500first_receipts=True,unchanged_original_parser=True,paired_baseline107_cached=True,final_checkpoint_files_checked=checks,full_optimizer_returned=True,no_paid_API=True,no_shutdown_sent=True,not_independent_audit=True))
 gate=d['frozen_gate'];headline='114出现达到事前参考条件的开发信号，保留为待确认候选；尚不能升级默认系统。' if gate['passed'] else '114未达到事前保留参考条件，停止当前matched_refresh配方扩大，继续保留107 label_only。'
 text=['# 114 matched_refresh：固定预算的第二轮样本更新','',headline,'',
 '从共同原Qwen3.5-9B底座新训练一个LoRA；第一轮原196条，第二轮155条匹配新例＋41条原例，共351个不同ID、392次呈现、50步。每槽患者、医生GT、作者来源和长度四分位匹配，每个优化批的GT组成不变；原分段均值CE、seed103027、BF16、micro1/累积8、lr1e-4、完整输入、prompt及三分类接口不变。两个短尾各4条，均按4归一；固定最后50步，不按评价成绩选checkpoint。', '',
 '新例S83/NS30/NA42；重复例NS32/NA9。两轮呈现仍各S83/NS62/NA51。总prompt tokens为3,270,682，比原两轮增加18。已知15个实际输入缺证例不进入新选样；155新例中150此前未审读，5个原unresolved保留GT且不加权。固定3个代表例已阅读实际完整reference，不能替代整批医学认证。', '',
 '仅使用原40名训练患者；评价为原20名选型患者的旧自然400／压力100，所有患者均有历史研究暴露。107旧500条预测完整复用，没有重训或重推基线；105只作历史保留。本轮没有理由监督、辅助头、新RAG、概率接口或阈值搜索。', '',
 '## 同ID实际结果','', '|面板／方案|有效N|MCC|PA|正确数|false-S/non-S|S／NS／NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for panel,v in d['panels'].items():
  for arm,m in v['scores'].items():
   label={'label_only107':'107 label_only（缓存）','matched_refresh':'114 matched_refresh','paper_r1':'paper_r1（作者历史）'}[arm]
   recall=' / '.join(pct(m['per_class'][g]['recall']) for g in L)
   text.append(f"|{panel} / {label}|{v['joint_valid_N']}|{m['mcc']:.4f}|{pct(m['percent_agreement'])}|{m['correct']}|{m['false_S']}/{m['non_S']}|{recall}|")
 text+=['','paper_r1只作同ID历史参照，不是当前同Judge同期强基线。自然与人为压力面板分开，不把500拼成自然总体。完整Macro-F1、AC1、各类precision/recall/F1、混淆矩阵及预测S假发现率见[comparison.json](comparison.json)。', '',
 '## 救回、误伤和风险变化','', '|面板|ΔMCC|ΔPA（百分点）|Δ正确|false-S新增／避免|S救／伤|NS救／伤|NA救／伤|ΔMCC患者95%CI|','|---|---:|---:|---:|---:|---:|---:|---:|---|']
 for panel,v in d['panels'].items():
  change=v['changes'];rs=[f"{change['by_class'][g]['rescued']}/{change['by_class'][g]['harmed']}" for g in L];ci=v['paired']['metrics']['mcc']['ci95']
  text.append(f"|{panel}|{v['delta_MCC']:+.4f}|{100*v['delta_PA']:+.2f}|{v['delta_correct']:+d}|{change['false_S_new']}/{change['false_S_avoided']}|"+'|'.join(rs)+f"|[{ci[0]:+.4f}, {ci[1]:+.4f}]|")
 text+=['','以下分别保留来源、患者方向和无效覆盖，避免只展示某类改善：','']
 for panel,v in d['panels'].items():
  q=v['candidate_coverage'];ps=v['patients'];text.append(f"- {panel}：收到{q['received']}，有效{q['valid']}，无效{q['invalid']}；NA从S改成NS而仍错{v['NA_S_to_NS_still_wrong']}条。患者正确数改善／下降／不变：{sum(r['correct_delta']>0 for r in ps)}/{sum(r['correct_delta']<0 for r in ps)}/{sum(r['correct_delta']==0 for r in ps)}。")
  for author,ms in v['author'].items():
   a,b=ms['label_only107'],ms['matched_refresh'];text.append(f"- {panel}/{author}：MCC {a['mcc']:.4f}→{b['mcc']:.4f}，正确{a['correct']}→{b['correct']}，false-S {a['false_S']}→{b['false_S']}。")
 n=d['panels']['natural'];p=d['panels']['pressure'];ns=n['scores']['matched_refresh'];bs=n['scores']['label_only107'];ps=p['scores']['matched_refresh'];pb=p['scores']['label_only107']
 detail=f"自然集正确S {bs['confusion_matrix'][0][0]}→{ns['confusion_matrix'][0][0]}、NS {bs['confusion_matrix'][1][1]}→{ns['confusion_matrix'][1][1]}、NA {bs['confusion_matrix'][2][2]}→{ns['confusion_matrix'][2][2]}。NA召回下降{100*(bs['per_class']['Not Addressed']['recall']-ns['per_class']['Not Addressed']['recall']):.2f}个百分点，超过事前5个百分点保护线；减少的错误放行中，3条只是把真实NA从S改为NS，仍然分类错误。压力集NS正确{pb['confusion_matrix'][1][1]}→{ps['confusion_matrix'][1][1]}，NA正确{pb['confusion_matrix'][2][2]}→{ps['confusion_matrix'][2][2]}，false-S没有净改善。两面板均未救回原先错误的NA，呈现明显向NS移动的取舍。"
 text+=['',detail,'',
 '自然正确S净增加1，没有出现大批正确S被压掉的净损失；真正的主要代价是NA识别下降。自然human来源净少9条正确、LLM来源净多6条；自然false-S净减少4，其中一个患者贡献3，不能把风险收益视为各来源、各患者普遍改善。NS召回上升是实测收益，尚不足以掩盖NA损失或宣布核验能力整体提高。', '',
 '患者级配对bootstrap为1000次；这些区间不覆盖历史开发选择、重新训练波动或跨医院泛化。区间跨0不等于没有任何作用，本次停止依据是具体NA损失及固定保护条件。', '',
 '## 决策和归因边界','',headline,'',f"事前质量信号={gate['quality_signal']}，风险信号={gate['risk_signal']}，保护条件={gate['guards']}。门槛见[冻结协议](../../tasks/114_matched_refresh/protocol.md)，不是看结果后调整的标准。", '',
 '本次只验证这一个固定样本更新配方。107是既有历史对照，114与107硬件不同，未补同期重复训练；即使出现正信号，也不能把全部差异唯一归因于数据覆盖。不同类获得的新例比例不同，新例也未全部经过临床审读。阴性结果不能概括为标签微调全部失败，也不能证明所有数据扩展均无效。没有自动追加种子、学习率、loss、采样、1317扩展、115或默认升级。', '',
 '## 时间、费用和归档','',f"任务从{cost['start_beijing']}至关键回执与完整checkpoint均已回传{cost['task_end_beijing']}，共{cost['task_wall_minutes']:.2f}分钟。GPU工作完成{cost['GPU_done_beijing']}，关键回执回传{cost['key_return_beijing']}，最终checkpoint回传{cost['final_checkpoint_return_beijing']}（与评价并行）。按¥1.58/小时估算本轮¥{cost['estimated_GPU_CNY']:.4f}/3，含准备等待、加载、最长样本检查、训练、500评价、保存及回传；API ¥0。平台精确账单未核实，历史费用不重置。", '',
 f"50步训练日志合计{cost['train_logged_seconds']:.1f}秒；500条评价{cost['eval_seconds']:.1f}秒，含正式首批。每条仍只需同一9B核验器，未增加投票组件。最长完整样本backward及LoRA梯度已实测通过；CPU自检、训练loss和梯度正常均不作为方法有效的证据。", '',
 '原始预测、日志、最终LoRA及完整optimizer/RNG状态已回传`.local_models/114_matched_refresh/evidence/`；本地最终checkpoint各文件与提交标记核验一致。远端`/root/autodl-tmp/verifact114/`保留两份滚动checkpoint；原107及全部旧结果未覆盖。', '',
 '按用户最新政策不发送shutdown、不释放实例或磁盘。实例保留开机时会继续计费；任务结束后的用户留机费用另列。当前本地成果未提交或推送，本轮没有新的发布指令；原完整main b3bac162、精简main f533f929不冒充114已归档。']
 c.put(O/'decision.json',dict(headline=headline,gate=gate,decision=d['decision'],no_automatic_next_task=True));c.put(O/'resource_summary.json',dict(max_training_peak_GiB=max(s['peak_allocated_bytes'] for s in steps)/1024**3,training_steps=50,training_presentations=392,full_checkpoint_returned=True))
 (O/'final_report.md').write_bytes(('\n'.join(text)+'\n').encode('utf-8'))
 progress=f"# 114实时进度\n\n状态：完成。50步训练、500条首次预测、完整最终checkpoint及关键回执均已回传并完成本地统计。预计剩余GPU工作：0分钟。\n\n任务计时：{cost['start_beijing']}—{cost['task_end_beijing']}，{cost['task_wall_minutes']:.2f}分钟，GPU估算¥{cost['estimated_GPU_CNY']:.4f}/3，API ¥0。\n\n{headline}\n\n自然MCC {bs['mcc']:.4f}→{ns['mcc']:.4f}，false-S {bs['false_S']}→{ns['false_S']}，正确NA40→30；压力MCC {pb['mcc']:.4f}→{ps['mcc']:.4f}，false-S16→16，正确NA41→32。\n\n未发送关机指令。18:13核实SSH仍可连接，GPU没有计算进程；实例继续开着仍计费。报告：outputs/114_matched_refresh/final_report.md。\n"
 for path in [P/'实时进度.md',O/'实时进度.md']:path.write_bytes(progress.encode())
 print(headline);print(c.canonical(cost))
if __name__=='__main__':main()
