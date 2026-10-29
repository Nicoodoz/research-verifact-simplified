"""Actual115 report and scoped checkpoint checks after all GPU returns."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
P=R/'.local_models/115_label_sum';O=R/'outputs/115_label_sum';L=c.LABELS
def pct(x):return '—' if x is None else f'{100*x:.2f}%'
def date(t):return datetime.fromtimestamp(t,timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
def main():
 d=c.read(O/'comparison.json');session=c.read(P/'session.json');key=c.read(P/'return_key.json');back=c.read(P/'return_checkpoint.json');done=c.read(P/'evidence/results/gpu_done.json');setup=c.read(P/'evidence/results/model_setup.json');train=P/'evidence/results/train';pointer=c.read(train/'resume.json');folder=train/pointer['slot'];header=c.read(folder/'checkpoint_complete.json')
 assert pointer['step']==header['step']==50 and pointer['consumed']==392 and c.sha(folder/'checkpoint_complete.json')==pointer['complete_sha256']
 checks={n:c.sha(folder/n)==h for n,h in header['files'].items()};assert all(checks.values())
 assert setup['fresh_base'] and setup['zero_initial_B'] and not setup['auxiliary_head'] and setup['objective']=='label_sum' and setup['value_sum_divisor']==360/196
 fp=header['fingerprint'];assert fp['code']==c.sha(R/'tasks/115_label_sum/worker115.py') and fp['config']==c.sha(R/'tasks/115_label_sum/config.json') and fp['data']==c.sha(P/'bundle/data/train.jsonl')
 steps=c.rows(train/'steps.jsonl');assert [r['step'] for r in steps]==list(range(1,51)) and [r['loss_divisor'] for r in steps if r['loss_divisor']!=8]==[4,4]
 ev=c.read(P/'evidence/results/evaluation_done.json');assert ev['N']==500
 end=max(key['returned_epoch'],back['returned_epoch']);prior=c.read(R/'outputs/114_matched_refresh/cost_status.json');prior_end=datetime.fromisoformat(prior['task_end_beijing']).replace(tzinfo=timezone(timedelta(hours=8))).timestamp()
 cost=dict(task=115,start_beijing=date(session['start_epoch']),task_end_beijing=date(end),GPU_done_beijing=date(done['epoch']),key_return_beijing=date(key['returned_epoch']),checkpoint_return_beijing=date(back['returned_epoch']),task_wall_minutes=(end-session['start_epoch'])/60,hourly_CNY=1.58,estimated_GPU_CNY=(end-session['start_epoch'])*1.58/3600,cap_CNY=3,API_CNY=0,train_logged_seconds=sum(r['seconds'] for r in steps),eval_seconds=ev['seconds'],checkpoint_parallel_with_evaluation=True,platform_exact_bill_confirmed=False,no_shutdown=True,historical_ledgers_unchanged=True,previous114_GPU_CNY=prior['estimated_GPU_CNY'],task_gap_idle_minutes=(session['start_epoch']-prior_end)/60,task_gap_idle_CNY_estimate=(session['start_epoch']-prior_end)*1.58/3600,task_gap_not_charged_to115=True,post_task_idle_separate=True)
 assert cost['estimated_GPU_CNY']<=3;c.put(O/'cost_status.json',cost)
 c.put(O/'final_selfcheck.json',dict(single_fresh_candidate=True,original196_unchanged=True,training50steps392=True,tail4_normalization=True,objective_is_reused106_normalized_sum=True,normalizer=360/196,auxiliary_head=False,prompt_reference_parser_unchanged=True,model_setup=setup,complete500_first_receipts=True,baseline107_cached=True,published_worker_and_config_match_execution_fingerprint=True,final_checkpoint_hashes=checks,full_optimizer_RNG_returned=True,independent_sklearn_metrics_match=True,no_paid_API=True,no_shutdown_sent=True,not_independent_audit=True))
 gate=d['frozen_gate'];keep=gate['passed'];headline='115达到事前开发参考条件，出现值得进一步确认的label_sum信号；当前仍保留107主基线。' if keep else '115未形成通过保护条件的综合增量，停止当前label_sum配方，保留107主基线。'
 text=['# 115 label_sum：全局归一的标签路径训练','',headline,'',
 '只新训一个候选，从原Qwen3.5-9B底座fresh LoRA开始，复用107原196条、seed103027、原顺序、两轮392次呈现和50步。标签值损失从`sum(CE)/L`改为`sum(CE)/(360/196)`，其他答案均值CE不变。360来自S83×1＋NS62×2＋NA51×3；固定常数保持全数据标签段平均力度为1，仍改变三类相对梯度。它不是完整JSON统一NLL或新算法。', '',
 'BF16、完整作者reference、104 prompt、LoRA r16/alpha32、micro1/累积8、lr1e-4、原优化器和固定最后50步均保持。两短尾各4条，按4归一。不续训107/109/114，不叠加114新例，不增加辅助头、理由、类别代价矩阵、阈值或约束解码。正式评价仍greedy、max_new_tokens384、原parser和batch2分组，无GT输入。', '',
 '原40名训练患者与20名选型患者隔离，不使用确认40选方法；所有患者已有研究暴露。107全部旧500预测复用，105不执行。选择理由、原论文和玩具推导边界见[执行前分析](analysis.md)，冻结判断见[协议](../../tasks/115_label_sum/protocol.md)。这不冒充执行106旧A800与三模型诊断的全部协议。', '',
 '## 同ID结果','', '|范围／方案|有效N|MCC|PA|正确数|false-S/non-S|S／NS／NA召回|','|---|---:|---:|---:|---:|---:|---|']
 for panel,v in d['panels'].items():
  for arm,m in v['scores'].items():
   name={'label_only107':'107 label_only（缓存）','label_sum':'115 label_sum','paper_r1':'paper_r1（历史）'}[arm];rec=' / '.join(pct(m['per_class'][g]['recall']) for g in L)
   text.append(f"|{panel} / {name}|{v['joint_valid_N']}|{m['mcc']:.4f}|{pct(m['percent_agreement'])}|{m['correct']}|{m['false_S']}/{m['non_S']}|{rec}|")
 text+=['','paper_r1仅作作者历史参照，不是当前同Judge同期强对照。自然与人为压力面板分报，不合并成自然总体。全部Macro-F1、AC1、类别precision/recall/F1、混淆矩阵、S假发现率及风险区间见[comparison.json](comparison.json)。','',
 '## 类别得失、风险和分层','', '|面板|ΔMCC|ΔPA（百分点）|Δ正确|false-S新增／避免|S救／伤|NS救／伤|NA救／伤|ΔMCC患者95%CI|','|---|---:|---:|---:|---:|---:|---:|---:|---|']
 for panel,v in d['panels'].items():
  z=v['changes'];rs=[f"{z['by_class'][g]['rescued']}/{z['by_class'][g]['harmed']}" for g in L];ci=v['paired']['metrics']['mcc']['ci95']
  text.append(f"|{panel}|{v['delta_MCC']:+.4f}|{100*v['delta_PA']:+.2f}|{v['delta_correct']:+d}|{z['false_S_new']}/{z['false_S_avoided']}|"+'|'.join(rs)+f"|[{ci[0]:+.4f}, {ci[1]:+.4f}]|")
 text+=['']
 for panel,v in d['panels'].items():
  q=v['candidate_coverage'];a,b=v['scores']['label_only107'],v['scores']['label_sum'];ps=v['patients']
  text.append(f"- {panel}：收到{q['received']}、有效{q['valid']}、无效{q['invalid']}。正确S/NS/NA分别为{[a['confusion_matrix'][i][i] for i in range(3)]}→{[b['confusion_matrix'][i][i] for i in range(3)]}；NA从S改NS但仍错{v['NA_S_to_NS_still_wrong']}条。患者正确数改善／下降／不变为{sum(p['correct_delta']>0 for p in ps)}/{sum(p['correct_delta']<0 for p in ps)}/{sum(p['correct_delta']==0 for p in ps)}。")
  for author,ms in v['author'].items():
   x,y=ms['label_only107'],ms['label_sum'];text.append(f"- {panel}/{author}：MCC {x['mcc']:.4f}→{y['mcc']:.4f}，正确{x['correct']}→{y['correct']}，false-S {x['false_S']}→{y['false_S']}。")
 n=d['panels']['natural'];a,b=n['scores']['label_only107'],n['scores']['label_sum'];z=n['changes']
 interpretation=f"自然集预测S总数{a['predicted_S']}→{b['predicted_S']}，其中正确S {a['confusion_matrix'][0][0]}→{b['confusion_matrix'][0][0]}。相对107少{z['false_S_avoided']-z['false_S_new']}次错误放行，同时误伤{z['by_class']['Supported']['harmed']}条原正确S、救回{z['by_class']['Supported']['rescued']}条原错误S；NS净多{z['by_class']['Not Supported']['rescued']-z['by_class']['Not Supported']['harmed']}条正确，NA净变化{z['by_class']['Not Addressed']['rescued']-z['by_class']['Not Addressed']['harmed']:+d}。自然总正确数{a['correct']}→{b['correct']}，PA变化{100*n['delta_PA']:+.2f}个百分点。这是明显的非S判定倾向及正确S损失，不是可接受的轻微取舍。压力集没有真实S，因此PA与false-S改善无法体现这项主要代价。"
 text+=['',interpretation,'',
 '采用1000次患者配对bootstrap；区间不包含历史开发选择、训练seed或新医院不确定性。区间跨0不独自判阴性，也不以单类召回上升代替整体核验能力。本次停止首先依据实际正确S大量损失，而非单凭显著性门槛。', '',
 '## 判断与下一步边界','',headline,'',f"固定质量信号={gate['quality_signal']}，风险信号={gate['risk_signal']}，保护项={gate['guards']}。本轮不根据结果修改归一常数、权重、样本、prompt、学习率、epoch或阈值。", '',
 '这检验了一个成熟训练目标在临床核验标签接口上的适配。实际结果不支持把移除逐样本逆长度权重当作可靠分类改进；NS与风险点估计改善主要伴随决策倾向变化。不能由此宣布所有序列目标均无效，也不能证明107的均值目标就是此前失败主因。107历史训练硬件与115不同，尚无同期同卡重训控制；196条筛选、单seed、开发选型暴露和原GT完整EHR与实际reference差异仍限制归因。', '',
 '仍不能唯一判定新模型退化中，优化轨迹、泛化与共享Not前缀下的greedy路径失配各占多少。本轮没有给115另采完整标签路径概率；113针对107的旧评分结果不能冒充115的解码诊断。补做需一次另行固定的路径评分检查，不能从已有文本反推概率；鉴于当前500条的实际代价巨大，本轮不为此重启GPU或换评分挽救成绩。', '',
 '当前建议收束到107主基线及其可辩护验证与论文整理，暂停继续调整类别倾向的小配方。若后续继续研究，首先需要解决明确的证据范围/监督可辨识问题，或为保留下来的107补必要同模型强对照；不能把更多未验证模块当成下一步。当前不自动扩大1317、追加种子或116，不升级默认系统。', '',
 '## 费用、保存及发布','',f"从{cost['start_beijing']}至关键材料齐备{cost['task_end_beijing']}，共{cost['task_wall_minutes']:.2f}分钟，按¥1.58/小时估算本轮¥{cost['estimated_GPU_CNY']:.4f}/3，API ¥0。GPU结束{cost['GPU_done_beijing']}；checkpoint于{cost['checkpoint_return_beijing']}与评价并行回传，关键回执于{cost['key_return_beijing']}回传。包含分析准备、等待、加载、最长backward检查、训练、评价和保存回传；精确平台账单未核。", '',
 f"50步日志合计{cost['train_logged_seconds']:.1f}秒，500评价{cost['eval_seconds']:.1f}秒；原始结果、最终LoRA、完整optimizer/RNG和日志已回传`.local_models/115_label_sum/evidence/`并核对完整提交标记。历史114费用仍为¥{cost['previous114_GPU_CNY']:.4f}，未重置；114结束到115接续间留机约{cost['task_gap_idle_minutes']:.2f}分钟、估算¥{cost['task_gap_idle_CNY_estimate']:.4f}另列，不计115。任务结束后的留机费用也另列。", '',
 '未发送shutdown，不释放实例或磁盘；计算停止不代表GPU停止计费。用户已授权本轮完成后双仓库提交推送，并补归档113/114允许公开的既有成果；成功状态以最终远端main核验及交付提交号为准。临床原文、原始私有回执、凭据、模型及缓存不进入GitHub。']
 (O/'final_report.md').write_bytes(('\n'.join(text)+'\n').encode());c.put(O/'decision.json',dict(headline=headline,gate=gate,decision=d['decision'],no_automatic_next_task=True))
 progress=f"# 115实时进度\n\n状态：完成。50步训练、500条首次预测及完整checkpoint/关键回执已回传。剩余GPU工作：0分钟。\n\n{headline}\n\n本轮{cost['task_wall_minutes']:.2f}分钟，GPU估算¥{cost['estimated_GPU_CNY']:.4f}/3，API ¥0，任务计时{cost['start_beijing']}—{cost['task_end_beijing']}。未发送关机；继续开机仍计费。\n\n报告：outputs/115_label_sum/final_report.md。当前进入本地统计/发布收尾。\n"
 for path in [P/'实时进度.md',O/'实时进度.md']:path.write_bytes(progress.encode())
 print(headline);print(c.canonical(cost))
if __name__=='__main__':main()
