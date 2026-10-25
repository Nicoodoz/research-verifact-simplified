"""Chinese report and paper-facing sections from actual final artifacts."""
from pathlib import Path
import common095 as c

NAMES={'Original':'原VeriFact，同ID发布预测','B_raw':'B原生判定','B_PriorG':'B＋Frozen PriorG','B_U0':'B分数最高类U0','B_U2':'B固定U2','092_Frozen':'092 Frozen（患者OOF）','092_Finetuned':'092 Fine-tuned（患者OOF）','B':'同期B','E':'E：原文锚点','C':'C：锚点＋最小差异对照'}
def table(tt):
    if not tt:return '无可评价共同集合。\n'
    out=['|实验配置|MCC|PA|正确/N|错误支持/non-S|AC1|Macro-F1|','|---|---:|---:|---:|---:|---:|---:|']
    for k,z in tt.items():out.append(f"|{NAMES.get(k,k)}|{z['MCC']:.4f}|{z['PA']:.2%}|{z['correct']}/{z['N']}|{z['false_S']}/{z['true_non_S']}|{z['AC1']:.4f}|{z['Macro_F1']:.4f}|")
    return '\n'.join(out)+'\n'

def class_table(tt):
    out=['|配置|S precision/recall/F1|NS precision/recall/F1|NA precision/recall/F1|NS→S|NA→S|','|---|---|---|---|---:|---:|']
    for k,z in tt.items():
        triples=[' / '.join(f'{z[field][i]:.3f}' for field in ['precision','recall','F1']) for i in range(3)];cm=z['confusion_matrix'];out.append('|'+NAMES.get(k,k)+'|'+'|'.join(triples)+f'|{cm[1][0]}|{cm[2][0]}|')
    return '\n'.join(out)+'\n'

def pair_table(pp):
    out=['|比较|救回/伤害/净正确|患者胜/负/平|ΔPA 95%区间(pp)|ΔMCC 95%区间|','|---|---|---|---|---|']
    for name,z in pp.items():
        if not z:continue
        pa=z['CI95']['PA'];mc=z['CI95']['MCC'];out.append(f"|{name}|{z['rescue']}/{z['harm']}/{z['net']:+d}|{z['patient_win_loss_tie']}|[{pa[0]*100:+.2f},{pa[1]*100:+.2f}]|[{mc[0]:+.4f},{mc[1]:+.4f}]|")
    return '\n'.join(out)+'\n'

def write(name,text):
    with (c.OUT/name).open('w',encoding='utf-8',newline='\n') as f:f.write(text.strip()+'\n')

def main():
    from baseline_cases095 import main as write_baseline_cases
    write_baseline_cases()
    from interpret095 import main as write_findings
    write_findings()
    cov=c.read(c.OUT/'baseline_coverage.json');bm=c.read(c.OUT/'baseline_metrics.json');bp=c.read(c.OUT/'baseline_paired.json');cost=c.read(c.OUT/'cost_ledger.json');gate=c.read(c.OUT/'operation_gate.json');screen=c.read(c.OUT/'screen_analysis.json') if (c.OUT/'screen_analysis.json').exists() else None;dec=c.read(c.OUT/'screen_numeric_decision.json') if screen else None
    default=bm['common_core']['B_PriorG'];original=bm['common_core']['Original'];gain=bp['B_PriorG-Original'];boundary=bp['B_PriorG-B_raw'];complete='全部9065个ID已有当前B成功回执' if cov['full_B_complete'] else f"当前B成功覆盖{cov['successful_B']}/9065，仍缺{cov['missing']}条，**不能称全量B完成**"
    decision=c.read(c.OUT/'final_decision.json');conclusion=decision['conclusion_zh']
    lead=f'''# 095 先读这个：全量基准、来源诊断与最小差异对照核验

**{conclusion}** 默认仍为C48 → DeepSeek T-S无示例B（thinking-high）→ Frozen PriorG，本轮不自动升级或启动下一任务。

{complete}。其中core有效{cov['core_valid_B']}、raw有效{cov['raw_valid_B']}；成功但core无效{cov['HTTP200_core_invalid']}条保留原回答，不因失败或成绩重发、不填旧标签。新增收费目录价及未知预留合计 **¥{cost['total_directory_price_or_unknown_cny']:.6f}/150**；{cost['attempts']}次尝试、{cost['HTTP200']}个HTTP200、{cost['retry_attempts']}次重试。

## 结论先行

1. 在当前B共同core有效的{cov['core_valid_B']}个同ID上，B＋G相对原作者净正确{gain['net']:+d}，MCC {original['MCC']:.4f}→{default['MCC']:.4f}，Macro-F1 {original['Macro_F1']:.4f}→{default['Macro_F1']:.4f}，错误支持{original['false_S']}→{default['false_S']}。这是当前系统比较，不能归为本轮新对比操作的贡献，也不是独立外部测试。
2. 同一B回答的raw→PriorG产生{boundary['rescue']}救回、{boundary['harm']}伤害，净{boundary['net']:+d}；新增/避免错误支持为{boundary['false_S_added']}/{boundary['false_S_prevented']}。固定决策边界改变标签，不代表找到了新病历信息。
3. 指定的唯一新候选完成300条构造；程序来源通过{gate['program_valid']}条，自动核对拟触发{gate['automated_eligible']}条（自然{gate['automated_eligible_panels'].get('natural',0)}、富集{gate['automated_eligible_panels'].get('mechanism',0)}）。数量gate通过，但来源内容审查发现时点、对象关系和并列作用域误放行，语义实施gate失败，实际候选最终Judge调用为0。自动标记不等于真实合格，不能把未执行写成分类阴性或等效。
4. 80例/50患者的发现性阅读说明状态、数值、事件范围及分数边界混杂；对来源不足保留unknown，不新增医生gold。四例有限包外搜索没有建立新的包外见证；一条最初未定位的目标日期信息在完整C48中找到，已追加补正。

全量系统优势有明确类别来源：相对原作者，S/NS/NA分别净正确{gain['rescue_by_GT']['Supported']-gain['harm_by_GT']['Supported']:+d}/{gain['rescue_by_GT']['Not Supported']-gain['harm_by_GT']['Not Supported']:+d}/{gain['rescue_by_GT']['Not Addressed']-gain['harm_by_GT']['Not Addressed']:+d}。NA召回由{original['recall'][2]:.2%}升至{default['recall'][2]:.2%}，S召回{original['recall'][0]:.2%}→{default['recall'][0]:.2%}、NS召回{original['recall'][1]:.2%}→{default['recall'][1]:.2%}。因此可主张PA/MCC/Macro-F1与错误支持的综合优势，不能主张各类召回全面提高。

## A：完整母体、缓存与有效性

母体为092的100患者9065有效atomic claim（S/NS/NA=7035/693/1337），原GT、原作者预测及时间元数据异常不变。历史20 exploration、40 development、40 reserved在本轮均经用户授权可用；全部已暴露，不称新holdout。036的早期最终验证地位不继承到T-S/PriorG或本轮。

扫描outputs与.local_models中40777份标准原生request.json，得到2479兼容成功回执、1885不同ID；按最早成功UTC、请求路径、回执路径选取，不按有效性或正确性选优。14条core无效的入选旧回执仍保留。claim/reference、system prompt、模型、thinking、输出接口一致；仅显式默认参数做等价规范化。扫描范围与其他非标准容器核查边界见独立阶段A报告，不能宣称任意外部缓存绝无遗漏。

逐ID实际reference来源保持：032冻结3675、036冻结3573、本地BGE补齐1817。后者不冒称与API检索逐字等价。新增B沿固定ID哈希顺序补缺；任何阶段已有同ID/同body成功B均可复用，包括core无效HTTP200，不重复制造更好答案。原方案规定D的同期B与历史主表选择分开；实际D最终比较未运行，历史答案没有被替换。

092两臂保持原五折患者OOF；B和Frozen PriorG没有按这五折重新训练或拟合，并包含历史提示开发、先验与校准材料的暴露。相同ID比较描述已冻结系统，**不表示所有系统具有同等训练监督或无开发暴露的OOF地位**。本轮不为改善表格而重新拟合B。

### 完整9065：已有作者与092对照

{table(bm['full_9065_existing'])}

### 同ID共同core集合：所有配置

{table(bm['common_core'])}

{class_table(bm['common_core'])}

### 原生标签自己的共同有效集合

{table(bm['common_raw'])}

{pair_table(bp)}

全9065逐行大表包括缺失与无效字段，不删ID：[统一预测](unified_9065_predictions.jsonl)；[覆盖](baseline_coverage.json)；[剩余ID](baseline_remaining.jsonl)；[剩余费用估算](baseline_gap_forecast.json)。原生有效而分数无效{cov['raw_valid_score_invalid']}条，原生无效而分数有效{cov['raw_invalid_score_valid']}条。保守已知正确/9065为{cov['core_correct_lower_bound_on_9065']:.2%}，是覆盖下界，不替代三分类共同有效PA/MCC。

这里raw有效指**冻结解析规则下有效**；其余响应不一定完全没有出现verdict字段。独立复核发现，少量截断文本虽有verdict片段，但未完成核心分数字段会被原严格解析契约一并拒绝。本轮不事后修改解析或补标签，详见[解析边界说明](parser_boundary_note.md)。

![基准混淆矩阵及覆盖](baseline_confusion_coverage.png)

![共同core集合的质量与错误支持](baseline_quality_risk.png)

[患者、human/LLM、证据来源、调用批次及数据异常分层](baseline_strata.json) · [NS→S/NA→S和逐例救回伤害](baseline_case_transitions.jsonl) · [类别转移](baseline_class_transitions.json)。患者bootstrap固定预测重抽1000次，不包含开发选择或服务波动，区间跨零不解释为等效。

[结果解释](baseline_findings.md)进一步列出三类救回/伤害、raw与分数最高类的分歧、常见评分组合、患者分布、来源分层及历史重复，区分边界作用、病例组成和未测批次影响。

## B：源文定位与历史去重

[历史差异表](history_difference.md)核对004/013、028–031、042–049、065–070、079–083、093–094。过去已有要求分解、引用、关系Gate、补证、聚焦及学习融合；本轮没有把它们换名。特别保留067 v1实现失败/v2来源争议、043成功定位条件集合、048仅触发子集、093低实际操作率、094引用无效相关净差等限制。

发现80例含raw正确被G改错16、G救回raw错误12、作者正确B错16、B正确作者错12、双方错12及正确保护12；S/NS/NA=30/32/18，非自然错误率调查。执行者和独立来源复核者各40。多数读取相关完整来源条目，部分整包回查；并非80份完整EHR逐字穷尽。阅读显示原文已有判别信息、事件/日期/对象对应、范围与模态、边界取舍以及无法判断同时存在。模型reason只作输出材料，不作为医学机制自证。

[80例可核查记录](source_review_80.jsonl) · [读取范围与分布](source_review_80_summary.json) · [补充回查与四次包外搜索](source_review_supplement.json)。这80个ID全部排除于首轮和扩量，患者本身仍有开发暴露。源文见证不等于新医生gold，模型核对器通过也不认证近邻完整命题真值。

[B相对作者及raw→G的代表性救回/伤害](baseline_cases.md)连接到同ID最终表，既展示可定位关系，也保留日期/范围unknown。它们是发现性解释，不作为新候选分类效果或原作者内部推理原因的证据。

## C/D：唯一冻结操作与辨识性对照

辅助构造器只读原claim、原C48，以一次连续跨度替换构造一个近邻。新取值必须在1–2个原文锚点内出现，程序核验引用与偏移，第二个有限辅助检查确认单属性、实质差异、同事件与不编造。辅助均为同0731的非thinking接口，不训练核心模型。最终Judge保持T-S thinking-high、8192输出上限、temperature0；原claim和完整reference不变。

E只添加实际原文锚点；C在完全相同锚点上再添加明确标为生成假设的近邻及比较要求。允许两说法同时支持、同时不支持或无法区分；不强制二选一，不把未找到候选变成NA/NS。构造/来源/核对失败时E/C精确别名到B，不增加不可用提示再发Judge。

首轮自然200、富集100在任何候选结果前冻结；自然按ID哈希，富集按固定标签/属性词/患者规则，包含原本正确病例，不按历史能修好的错误抽样。自然实际162S/14NS/24NA，富集34S/33NS/33NA，分报而不合并为全量PA。程序与核对器判定决定部署，人工作源文检查不逐例选择应用。

主比较C−B看系统收益，C−E看对比增量，E−B看辅助摘录/呈现。主结果同一Frozen PriorG；raw/U0/U2诊断不事后选优。明确继续、停止、边缘扩量条件在结果前冻结于[协议](../../tasks/095_anchored_minimal_contrast/experiment_protocol.md)与[口径澄清](../../tasks/095_anchored_minimal_contrast/decision_clarification.md)。
'''
    if screen:
        for panel,title in [('natural','自然组成面板'),('mechanism','少数类/机制富集面板')]:
            d=screen['panels'][panel];lead+=f"\n### {title}\n\n冻结N={d['N']}，真实触发{d['operated_N']}，core共同有效{d['core_N']}，raw共同有效{d['raw_N']}。\n\n最终：\n\n{table(d['metrics']['PriorG'])}\n{class_table(d['metrics']['PriorG'])}\n原生raw（自身有效分母）：\n\n{table(d['native_raw_metrics'])}\n{pair_table(d['comparisons']['PriorG'])}\n{pair_table({('raw '+k):v for k,v in d['comparisons']['raw'].items()})}\n"
        lead+='\n![首轮效应与真实覆盖](screen_effect_coverage.png)\n\n触发子集、invalid、作者/来源分层与raw→G归因见[主分析](screen_analysis.json)、[逐例转移](screen_transitions.jsonl)、[构造出处](construction_audit.jsonl)。[代表性救回/伤害](candidate_cases.md)根据原文、输入和真实输出解释，不把一次分数越界等同临床关系学会。\n'
        lead+=f"\n预登记数值决策为`{dec['signal']}`；最终条件式扩量/停止说明见[决策](final_decision.json)。"
    else:
        lead+='\n数量门槛已通过，但实际单属性、同事件与保留限定的语义检查失败，因此没有执行收费B/E/C最终分类比较。不能把未测分类写成方法负效果或E/C与B等效。[逐ID实际部署状态](construction_deployment_status.jsonl)区分自动eligible与最终调用；旧构造审计的operated字段仅是自动拟触发标记，不代表已运行Judge。16例预检中3个自动通过均存在确定问题或unknown；另固定抽查24个自动通过输出，发现既有可读的单属性假设，也有同义改写、多属性、关系借用与时点迁移，详见[质量复核](construction_quality_summary.json)和[案例说明](candidate_cases.md)。这些人工阅读不转成逐例部署名单。只修复了5条空白绑定错误，复用原成功回答；没有通过改提示追逐更高通过率。A与F继续完成。\n'
    lead+=f'''

## E：扩量与稳定性边界

{decision.get('extension_zh','本轮未执行条件式扩量；未自动开启另一方案。')}

[既有B重复](repeat_analysis.json)使用同ID兼容请求的最早/最晚成功回答，不选最好答案。重复子集来自历史混合选样，不能据少量相同标签证明全系统稳定，也不能把缺少重复当方法无效。本轮未执行候选阶段同期B、额外批次桥接或顺序控制，历史缓存与新补齐的分层不能单独排除服务批次影响。

## 成本、恢复和可复现性

{cost['attempts']}次新尝试包含构造、核对、主Judge、重试及未知保留；未知保留¥{cost['unknown_reserve_cny']:.6f}，GPU新租赁0、检索新API0。既有缓存历史费用不重新计入本轮新增支出；整个部署的累计历史检索成本和092 GPU租金并非0，也未取得全部账单。

全覆盖所选B回答中，平均输入{cost['baseline_full_coverage_usage']['prompt_tokens']['mean']:.0f} token（中位{cost['baseline_full_coverage_usage']['prompt_tokens']['median']:.0f}，P95 {cost['baseline_full_coverage_usage']['prompt_tokens']['p95']:.0f}），平均输出{cost['baseline_full_coverage_usage']['completion_tokens']['mean']:.0f} token（中位{cost['baseline_full_coverage_usage']['completion_tokens']['median']:.0f}，P95 {cost['baseline_full_coverage_usage']['completion_tokens']['p95']:.0f}，包含thinking）。输出达到8192的有{cost['baseline_full_coverage_usage']['completion_at_8192']}条；是否有效仍以实际解析为准，不仅按长度判定。该usage摘要包括复用缓存，不全是本轮新增支出。

普通北京0731目录价忙时输入/输出/缓存输入3/9/0.3、闲时1.5/4.5/0.15元/百万token；官方普通服务公告核实22–08 UTC+8。初版保守忙时账本快照原位保留，新版只对同一闲时窗口的成功usage重算；HTTP0/未知始终保留最大bound。发送前SQLite事务检查所有已发生、未知、在途与下一请求上界，任务硬限150不变；不以赠金或促销扩大预算。

[总账](cost_ledger.json) · [每次尝试](attempt_ledger.jsonl) · [官方价核实](../../tasks/095_anchored_minimal_contrast/pricing_verification.md) · [工程修订](../../tasks/095_anchored_minimal_contrast/runtime_v3_note.md)。实际辅助构造与核对费用为¥{cost['phase_costs'].get('method',0):.6f}，是未进入最终分类之前已经发生的研究费用。本轮没有E/C实际部署成本或分类收益；未来部署估算必须包括失败构造后回B的辅助开销，共享构造不能重复记为本轮实际付费，也不能在单臂部署比较中当免费。

![成本与调用覆盖](cost_coverage.png)

复现与准确恢复入口见[任务README](../../tasks/095_anchored_minimal_contrast/README.md)。私有原文/回执/模型缓存不推送；公开数据只有ID、哈希、标签、分数、数值分析和抽象病例说明。不修改.gitignore、历史成果或默认系统。

## F：论文主张与复核

本轮最可靠的新成果是统一实际输入与有效性的同ID比较、可回查的原生→最终边界归因，以及指定对比构造的可行性预检和停止依据。最终对比分类未运行，已有B的优势不是095候选的创新；普通偏置、来源匹配和单点替换也不是未经论证的算法首创。

对比/独立核验已有QAGS、CoVe、RAFTS、VitaminC及2026 ACV等直接近邻。本轮只作患者证据约束下的简化适配与实测，不宣称复现或超过未运行的完整文献方法。ACV全文本次访问受阻，仅核到摘要，相关算法级差异不能过度主张。

论文方法/实验/讨论及贡献更新见[中文稿](manuscript_zh.md)；[精简证据地图](evidence_map.md)区分主结果、对照、动机、阴性与附录。不把数据集错误支持减少称为已证实降低临床伤害。

执行者[自检](selfcheck.json)与[独立复核](../../reviews/095_anchored_minimal_contrast/final_review.md)分别列范围。阶段A、设计和费用修订已有独立记录；最终审计必须以真实完成的复核为准，不能拿阶段PASS代替全任务PASS或独立医学审核。
'''
    write('report.md',lead)
    details=['# 095 详细数值表\n','各表同ID；类别顺序S、NS、NA。不同面板不混成总PA。\n']
    for name,tt in bm.items():details+=['## '+name+'\n',table(tt),class_table(tt),'混淆矩阵：\n']+[f"- {NAMES.get(k,k)}：`{z['confusion_matrix']}`" for k,z in tt.items()]
    if screen:
        for p,d in screen['panels'].items():
            for method,tt in d['metrics'].items():details+=['## '+p+' / '+method+' / common core\n',table(tt),class_table(tt)]+[f"- {k}：`{z['confusion_matrix']}`" for k,z in tt.items()]
    write('detailed_tables.md','\n\n'.join(details));print('Chinese report generated')
if __name__=='__main__':main()
