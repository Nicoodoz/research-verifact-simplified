"""Render completed105 analyses. No inference, training or external calls."""
import json
import common105 as c

def main():
 e=c.read(c.OUT/'evaluation.json');r=c.read(c.OUT/'a800_resources.json');q=c.read(c.OUT/'output_quality.json');p=c.read(c.OUT/'paired_transition_summary.json')
 names={'base_judge':'base_judge（未微调同prompt）','label_only':'label_only（仅标签监督）','evidence_brief':'evidence_brief（证据短理由监督）','paper_r1':'paper_r1（作者历史预测）'}
 pct=lambda v:f'{100*v:.2f}%' if v is not None else '无定义'
 fmt=lambda v:f'{v:.4f}' if v is not None else '无定义'
 report=['# 105：短证据监督与仅标签监督——最终报告\n']
 passed=e['decision']['continue_to_larger_training']
 report += ['**冻结实验已完成。事前开发继续门槛：'+('通过' if passed else '未通过')+'。** 这不是新患者论文确认，也不证明超过DeepSeek同Judge的verifact_ref。完整500条三臂首次回执与两款196条、2轮适配器均保留。GPU运行结束后要求用户手动关机，程序没有执行关机；平台状态与费用见单列费用记录。',
 '\n## 研究问题与实际控制\n',
 '本轮只检验：在同一原始Qwen3.5-9B、同一196条训练样本及同一评价条件下，证据引用和简短关系说明的监督是否比仅标签监督有额外收益。三组共同使用104新版prompt，重新运行未微调base_judge；103历史分数不抵作同期对照。两个适配器分别从原底座初始化，不加载103适配器。',
 '训练40名患者与评价selection20名患者隔离，后续40名确认患者没有新增评价。100人均有历史研究暴露；500中70条属于103旧180面板，其余也不称完全未接触holdout。自然400（S321/NS26/NA53）与压力100（NS50/NA50）分开，不按历史模型对错或104解释质量选评价条目。',
 '训练数据为104原196条（S83/NS62/NA51），机器辅助策展而非新医生gold。两臂同ID、同顺序、同完整claim/reference、同GT及prompt，只改变答案。两轮每臂50步、392次消费，尾批4条按4缩放；BF16 LoRA r16/alpha32、lr1e-4、micro1、累积8、恒定学习率，无量化/CPU卸载。loss为最终标签值平均CE与其余答案平均CE相加，两臂统一；因此不能把105与103不同数据、epoch、prompt和loss的差异当纯理由增量。',
 '三臂固定500输入token SHA逐条相等，batch8、greedy、关闭thinking、384输出上限、同parser。完整成功批次即使格式无效也不重发。GPU预检与测速只检查资源、没有optimizer更新，不作正式答案或临床效果判断。科学冻结与实际接续见[协议](../../tasks/105_brief_supervision/protocol.md)、[A800工程接续](a800_execution_amendment.md)。']
 appendix=['# 105指标附录\n\n混淆矩阵行GT、列预测，顺序S、NS、NA。主要指标来自统一evaluate/paired_compare；1000次患者cluster bootstrap，不覆盖历史选择、重训或新医院泛化。']
 for panel,label in [('natural','自然'),('pressure','压力')]:
  part=e['panels'][panel];report += [f'\n## {label}面板\n',f"冻结{part['frozen_N']}条，三臂共同有效{part['common_valid_N']}条；完整N覆盖和上下界见evaluation.json。",'\n|配置|MCC|PA|正确数|false-S/non-S|Macro-F1|NS召回|NA召回|','|---|---:|---:|---:|---:|---:|---:|---:|']
  for arm,v in part['metrics'].items():report.append(f"|{names[arm]}|{fmt(v['mcc'])}|{pct(v['percent_agreement'])}|{v['correct']}/{part['common_valid_N']}|{v['false_S']}/{v['non_S']}|{fmt(v['macro_F1'])}|{pct(v['per_class']['Not Supported']['recall'])}|{pct(v['per_class']['Not Addressed']['recall'])}|")
  report += ['\n|候选−参照|ΔMCC及95%CI|ΔPA（百分点）|救回/误伤/净正确|false-S新增/避免|','|---|---|---:|---:|---:|']
  for key,paired in part['paired'].items():
   new,base=key.split('__vs__');v=paired['primary']['metrics']['mcc'];x=p[panel+'/'+key]
   report.append(f"|{new}−{base}|{v['delta']:+.4f} [{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]|{paired['primary']['metrics']['percent_agreement']['delta']*100:+.2f}|{x['rescue']}/{x['harm']}/{x['rescue']-x['harm']:+}|{x['false_S_added']}/{x['false_S_prevented']}|")
  report += ['\n|候选−参照|S救回/误伤|NS救回/误伤|NA救回/误伤|患者净胜/负/平|','|---|---:|---:|---:|---|']
  for key in part['paired']:
   x=p[panel+'/'+key];report.append('|'+key.replace('__vs__','−')+'|'+'|'.join(f"{x['by_GT'][g].get('rescue',0)}/{x['by_GT'][g].get('harm',0)}" for g in c.LABELS)+f"|{x['patient_win_loss_tie']}|")
  appendix += [f'\n## {label}\n']
  for arm,v in part['metrics'].items():
   appendix += [f'\n### {names[arm]}\n',f"MCC 95%CI {v['confidence_intervals']['mcc']}；PA 95%CI {v['confidence_intervals']['percent_agreement']}；预测S假发现率 {pct(v['predicted_S_FDR'])}。",'\n|类别|precision|recall|F1|真实数|','|---|---:|---:|---:|---:|']
   for g in c.LABELS:
    z=v['per_class'][g];appendix.append(f"|{g}|{pct(z['precision'])}|{pct(z['recall'])}|{fmt(z['f1'])}|{z['support']}|")
   appendix += ['\n```text\n'+'\n'.join(str(row) for row in v['confusion_matrix'])+'\n```']
  appendix+=['\n### 作者分层\n','|作者|配置|MCC|PA|false-S/non-S|NS召回|NA召回|','|---|---|---:|---:|---:|---:|---:|']
  for author,table in part['author'].items():
   for arm,v in table.items():appendix.append(f"|{author}|{arm}|{fmt(v['mcc'])}|{pct(v['percent_agreement'])}|{v['false_S']}/{v['non_S']}|{pct(v['per_class']['Not Supported']['recall'])}|{pct(v['per_class']['Not Addressed']['recall'])}|")
 report += ['\n## 格式、解释与可追溯性\n','所有500条物理回执保留，invalid、截断及缺失不补旧答案；共同有效集指标不替代完整N覆盖。', '\n|配置|收到|有效|截断|严格JSON|非空relation|证据列表|逐字匹配引句/全部引句|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for arm in c.ARMS:
  v=q['arms'][arm];report.append(f"|{arm}|{v['N']}|{v['valid']}|{v['length_finish']}|{v['strict_json']}|{v['nonempty_relation']}|{v.get('evidence_list',0)}|{v.get('literal_in_same_reference',0)}/{v.get('quotes',0)}|")
 report += ['\n引用匹配是机械检查，不证明引用充分、关系正确或解释与标签语义一致。可生成relation不能单独作为方法收益；分类风险、少数类表现与源文解释应一起判断。没有新增医生复标、收费API或用模型修复答案。', '\n## 实测成本与资源\n','\n|训练臂|步数/消费|训练步骤累计分钟|其中检查点秒|稳定输入token/s|峰值allocated GB|','|---|---:|---:|---:|---:|---:|']
 for arm,v in r['training'].items():report.append(f"|{arm}|50/392|{v['step_wall_seconds']/60:.2f}|{v['checkpoint_seconds']:.2f}|{v['steady_tokens_per_second']:.1f}|{v['peak_allocated_bytes']/1e9:.2f}|")
 report+=['\n|评价臂|生成墙钟分钟|平均输出tokens|聚合输出tokens/s|峰值allocated GB|','|---|---:|---:|---:|---:|']
 for arm,v in r['evaluation'].items():report.append(f"|{arm}|{v['generation_seconds']/60:.2f}|{v['mean_output_tokens']:.2f}|{v['aggregate_generation_tokens_per_second']:.2f}|{v['peak_allocated_bytes']/1e9:.2f}|")
 report += ['\n费用从15:06起按用户报价¥7.98/小时累计，加历史最低估算¥4.503952及保留的未知区间；总¥20/累计GPU150分钟不重置。GPU计算完成不等于平台停止计费，最终费用与用户手动关机确认单列在a800_cost_status.json。API新增0。', '\n## 事前门槛与研究结论\n', '门槛逐项：`'+json.dumps(e['decision'],ensure_ascii=False)+'`。',
 '未通过时停止当前冻结配方的扩大，不追加epoch、prompt或后处理挽救成绩；通过也仅支持下一步受控开发，不自动进入确认患者或宣布论文成功。短理由的额外贡献必须体现在相对label_only的结果，而非只超过未微调基线。',
 '\n## 复现、保存与核验\n',
 '实例根目录`/root/autodl-tmp/verifact105`；每个训练臂的`results/train/<arm>/training_done.json`与`resume.json`指向最终checkpoint槽位。最终适配器、配置及训练日志已回传私有` .local_models/105_brief_supervision/a800/backup/`并核验SHA；完整optimizer及基础权重保留实例，不作为公开仓库内容。精确版本与科学配置沿原preparation_freeze和镜像锁；接续脚本在冻结包外。',
 '本地离线复现：先运行`evaluate105.py --results <私有结果目录>`，再运行`finalize_a800105.py --results <同目录>`及`write_a800_report105.py`，均通过`scripts/run_research.ps1`使用现有CPU环境。公开仅含判定、资源、指纹与报告，不含临床正文、解释正文、权重或凭据。执行者自检与历史独立工程复核分开，不冒充独立医生审计。']
 (c.OUT/'final_report.md').write_bytes(('\n'.join(report).rstrip()+'\n').encode())
 (c.OUT/'final_metrics.md').write_bytes(('\n'.join(appendix).rstrip()+'\n').encode())

if __name__=='__main__':main()
