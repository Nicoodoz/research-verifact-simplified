"""Render aggregate findings only; all clinical text remains private."""
import json
from pathlib import Path
import common104 as c


def main():
    s=c.read(c.OUT/'supervision_summary.json');p=c.read(c.OUT/'paired_manifest.json')
    a=c.read(c.OUT/'asset_summary.json');t=c.read(c.OUT/'token_summary.json')
    f=c.read(c.OUT/'finalization.json');teacher=c.read(c.OUT/'candidate_teacher_checked_manifest.json')
    cost=c.read(c.OUT/'api_cost_ledger.json');decision=c.read(c.OUT/'next_action.json')
    cost_stats=c.read(c.OUT/'cost_summary.json')
    q=s['independent_API']['by_phase']['quality'];d=s['independent_API']['by_phase']['dispute']
    distributions=[]
    initial=s['initial_state_by_GT'];final=s['state_by_GT']
    for label in c.LABELS:
        candidate=initial[label].get('candidate_gt_explained',0)
        distributions.append(f"|{label}|96|{candidate}|{final[label].get('gt_explained',0)}|{final[label].get('reference_gap',0)}|{final[label].get('unresolved',0)}|")
    n=p['N'];counts=p['retained_GT'];tokens=t['lengths']
    short=f'''# 104：一页结论（2026-10-28）

**已完成监督诊断与配对数据构建，尚未检验分类提升。** 严格限定103的40名训练患者、原512条；全部96 NS、96 NA和固定hash96 S先看完整claim/reference，288份盲审封存后才连接医生GT。另224 S仅完成清单与token盘点，未冒充语义核验。未租GPU、未训练、未补跑27B，历史结果、原GT及默认系统保留。

现有材料同时暴露了**输入解释性与关系边界问题**，不能把103的风险恶化简单归因于NS数量少，也不能把全部首审分歧认定为医生错标。原reference未变时，NA中32/96被盲审为“部分支持/不完全支持”、6/96为支持；这提示“目标事实是否已涉及”的边界需要显式监督。首审13/288被标为输入缺口，其余分歧仍需单列歧义，不能据此宣布主因已经确定。原作者R1的reason与推理记录512/512已存在；任何同reference且预测等于GT的教师理由覆盖S318/320、NS78/96、NA59/96，仍须逐条语义检查。

|原GT|本轮审查|初步候选|最终配对|输入缺口待核|未解决歧义|
|---|---:|---:|---:|---:|---:|
{chr(10).join(distributions)}

交付**{n}条×2臂**：`label_only`（仅原医生标签）与`evidence_brief`（少量原文、短关系说明及同一标签），同ID、患者、GT、claim、reference、prompt与顺序，仅答案不同。保留{p['retained_patients']}名训练患者，类别为S {counts.get('Supported',0)} / NS {counts.get('Not Supported',0)} / NA {counts.get('Not Addressed',0)}；已审但隔离{s['quarantined']['N']}条，另224条S未语义审查，均不进入任一臂。无锚NA {p['no_anchor_na']}条单列。正文、原始教师理由、审查原稿、修订记录与可训练JSONL均留本地私有目录，GitHub只发布元数据、指纹与代码。

初步198条的教师策展处理：{json.dumps(teacher['actions'],ensure_ascii=False)}。固定API核查64次，质量有效{q['valid_N']}/{q['N']}、争议有效{d['valid_N']}/{d['N']}；候选推荐为{json.dumps(q['recommendations'],ensure_ascii=False)}。截断坏答案保留且不重发，不把HTTP200都当语义核查通过；最终逐条处置{f['manual_post_audit_N']}条。额外子代理盲复核8/16完成后因额度中断。争议不挽救非候选进入训练，不以模型投票修改GT。

CPU验证：两臂输入token逐例完全相同，prompt/padding的loss=-100，答案与EOS参与loss；原文引句逐字定位并保留全部重现位置。实际最大总长度标签版{tokens['label_total_tokens']['max']:,}、理由版{tokens['brief_total_tokens']['max']:,} tokens，无截断；平均新增答案{tokens['added_answer_tokens']['mean']:.1f} tokens。新增API目录价（不计缓存优惠）及未知预留共**¥{cost['used_or_reserved_cny']:.6f}/20**，未知/在途¥{cost['unknown_or_inflight_cny']:.6f}；{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200。GPU新增0。

**唯一下一步：{decision['recommendation_zh']}** {decision['reason_zh']} 这只是后续建议，本轮没有授权或启动下一笔GPU支出。

[详细报告](report.md) · [512资产清单](asset_inventory512.jsonl) · [288状态](review_status288.jsonl) · [最终配对指纹](paired_manifest.json) · [费用](api_cost_ledger.json)
'''
    details=f'''# 104：训练监督诊断与证据短理由数据构建

{short.split('[详细报告]')[0].split(chr(10),2)[2]}
## 数据、盲审与既有监督

512条完整清单见[asset_inventory512](asset_inventory512.jsonl)，医生一致性见[annotation_summary](annotation_summary.json)，来源核对与重复限制见[asset_inventory_notes](asset_inventory_notes.md)。没有claim规范化后的精确重复；登记的一组近重复只是词法候选，不等于确认的语义重复。医生首轮三人一致为S263/320、NS10/96、NA24/96；最终GT保留。该差异可能反映三类边界难度，不证明医生标签错误。

候选教师从本地发布数据提取，逐项核对proposition ID、claim SHA、reference ID与内容SHA；排除其他reference的理由。完整reasoning_chain只登记覆盖，不用作训练长思维链。教师优先级事前固定，不按103历史对错挑选。来源与GT一致只允许进入策展队列。修订次数不等于错误理由数，很多修订是在合格事实基础上补全关系、精简或删去不必要限定；实际沿用、修订、拒绝及新稿见[teacher_provenance](teacher_provenance.jsonl)。179条初步候选有合格来源教师、19条没有；这是来源覆盖，不是语义质量通过数。

首审由root24、semantic_b132、semantic_c132条构成，逐条完整阅读实际reference；原稿与分工SHA见[blind_review_freeze](blind_review_freeze.json)。当前Codex上下文已有项目标签规则和历史风险背景，所谓盲审仅指逐条GT及教师答案在首判前未打开，不是医学双盲或新患者验证。另有第四子代理对固定16条争议中的8条完成不看GT/首审/教师的独立完整审查，随后因代理额度限制退出；额外8条未完成，不冒充16条全部通过。固定16条API争议面板另行完整执行；结果与范围见[独立争议复核](independent_dispute_summary.json)。所有100名患者有历史研究暴露，本轮只维护训练角色边界。

## 具体发现与可追溯例证

见[case_findings](case_findings.md)。公开例证仅给ID、问题类型与私有台账位置，不发布临床原文。每条原文引用在私有行级`metadata.evidence_spans`保留Python字符offset、quote SHA与全部出现位置；实际发布reference没有原note ID时留null，不能把显示编号当作note ID。相同来源与精确引用都不等于关系正确。

初步候选198只表示首判与GT一致且结构/置信规则通过。质量核查以当前完整reference为边界；不查其他EHR后偷偷补入，不把“没找到某词”当反证，不把主题相关自动当部分支持。13条首审输入缺口与77条歧义是机器辅助诊断状态，不是修改原医生标签的依据。没有对未审224 S外推可学性，也没有用288的人为平衡分布估计全512问题率。

## 固定质量核查与修订

冻结规则见[protocol](../../tasks/104_supervision_evidence/protocol.md)，实际请求冻结见[api_audit_freeze](api_audit_freeze.json)，固定样本见[api_audit_samples](api_audit_samples.jsonl)。质量每类16条；争议16条来自首审分歧的固定hash，没有看到API分类后重选。API只判断理由忠实性、对象/时间和限定，不产生新的医生gold或重新跑103评价。采样质量推荐与布尔检查见[api_quality_checks](api_quality_checks.jsonl)；最终接纳/修订/隔离见[final_quality_status](final_quality_status.jsonl)。采样通过不认证其余全部样本，已知关键问题不得留在最终包。

后续修订承接教师策展版本并保留其来源元数据；首审原件、initial GT join、原候选、teacher_checked与最终paired分开，未覆盖旧SHA。明确隔离的争议不因API赞同GT被强行救回训练。审查和解释均为机器辅助监督，不是新增医生复标，不证明训练能完整学会推理。

## 可训练包、接口与CPU验证

私有入口：`.local_models/104_supervision_evidence/paired/label_only.jsonl`与`evidence_brief.jsonl`。行级`answer`是JSON字符串，`answer_text`冗余校验。原GT仅元数据；两臂相同共享prompt，理由版不另加额外输入。共享prompt较103原prompt有输出格式与边界说明调整，因此未来必须保留同一新prompt的未微调9B基线，不能直接用103历史分数抵作同期基线。

原512的实际输入统计见[inventory_token_summary](inventory_token_summary.json)，最终包见[token_summary](token_summary.json)。固定复用103的9B tokenizer revision `{t['revision']}`，只加载tokenizer与Jinja，不加载模型权重；CPU实际编码、引用、隔离、JSON、loss mask及尾批检查全部完成。103旧worker会按GT重建答案并硬编码512和8条累积，不能直接读取新文件就宣称训练理由；[接入说明](../../tasks/104_supervision_evidence/README.md)给出替换点，`training104.encode_lists`保持103返回接口，尾批按实际N消费、不丢样本。没有实现或运行新GPU优化器循环，权重/optimizer/RNG恢复仍属未来训练工程。

两个配对包都只用最终{n}条，不能把理由版与原完整512标签版当公平对照。保留/隔离的类别、作者、患者见[supervision_summary](supervision_summary.json)；未审224 S另列，不混为隔离后语义失败。测试与范围见[selfcheck](selfcheck.json)和[工程复核](../../reviews/104_supervision_evidence/engineering_review.md)，不冒充独立医生审计。

## 下一步与费用

{decision['recommendation_zh']}。{decision['reason_zh']}

未来若开展训练，三臂为`base_judge`（未微调同模型同prompt）、`label_only`和`evidence_brief`；两个训练臂同子集、顺序、超参数及模型，不能换更强模型制造收益。预先联合约束自然MCC、PA、false-S与NS召回，并单报压力：相对同样本标签版自然ΔMCC≥0.02或false-S/non-S下降≥5个百分点，同时PA下降≤2个百分点、自然false-S增加≤2个百分点、NS召回下降≤5个百分点；压力false-S不得增加、NS召回下降≤5个百分点。报告患者配对区间与固定重复，不在103的180条选型结果上搜索后处理。具体新患者角色、规模、预算还须新任务冻结；104的数据构造不能当作分类收益。

收费API固定DeepSeek V4 Flash 0731、thinking-high、temperature=0、top_p=1、max_tokens=8192，限质量/争议核查；官方价格和时段依据见[pricing_verification](../../tasks/104_supervision_evidence/pricing_verification.md)。64次回执均按忙时目录价输入3元、输出9元/百万tokens计费，不用渠道折扣或缓存命中扩大额度；总额¥{cost['used_or_reserved_cny']:.6f}，每次平均¥{cost_stats['total']['mean_per_attempt_cny']:.6f}，未知/在途¥{cost['unknown_or_inflight_cny']:.6f}。每次请求预留、回执、SQLite账本与费用分解可本地复核，[公开账本](api_cost_ledger.json)、[分阶段费用](cost_summary.json)与[token usage](api_usage.jsonl)不含正文。目录价估算不是平台最终发票；无GPU租赁、无模型下载、无新分类评价。

## 工件导航

- [完整512资产](asset_inventory512.jsonl)、[医生一致性](annotation_inventory512.jsonl)、[实际token清单](inventory_token_lengths512.jsonl)。
- [288首审状态](review_status288.jsonl)、[隔离清单](quarantine.jsonl)、[最终配对manifest](paired_manifest.json)、[最终处理](finalization.json)。
- [教师队列来源](teacher_queue_manifest.json)、[逐条教师来源](teacher_provenance.jsonl)、[策展包manifest](candidate_teacher_checked_manifest.json)。
- [构建与复现说明](../../tasks/104_supervision_evidence/BUILD_RUNBOOK.md)、[实际输入指纹](analysis_inputs.json)、[隐私模式扫描](public_privacy_scan.json)。

私有目录包含原文、完整解释与回执，不随Git发布。仅clone公开仓库不足以训练，须使用已获数据使用授权的本地材料。完整归档仓库保留全部允许发布104成果，精简仓库保留关键成果；两个仓库outputs外相同。本轮不升级默认，不自动开展下一实验。
'''
    for name,body in [('summary.md',short),('report.md',details)]:
        (c.OUT/name).write_bytes(body.encode('utf-8'))
    print(c.canonical(dict(report=True,N=n,cost=cost['used_or_reserved_cny'],next_action=decision['action'])))


if __name__=='__main__':main()
