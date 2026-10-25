"""Synchronize current navigation and freeze delivery hashes; no historical rewrites."""
import common093 as c
def replace(path,old,new):
    p=c.ROOT/path;b=p.read_bytes();nl='\r\n' if b'\r\n' in b else '\n';s=b.decode('utf-8');a=old.replace('\n',nl);z=new.replace('\n',nl)
    assert a in s,path
    p.write_bytes(s.replace(a,z,1).encode('utf-8'))
def main():
    replace('AGENTS.md','092结项后','093结项后')
    replace('AGENTS.md','- 092已完成双臂全量OOF','- 093已完成重复原文折叠/固定预算补证首轮：自然共同有效88条B/F/A正确76/77/76，压力30条17/16/18；停止本版，默认不变，费用¥4.097118/20。用户本轮允许现有全体患者材料，实际同期120条；不自动扩大或094。[093报告](outputs/093_lossless_evidence_budget/report.md)。\n- 092已完成双臂全量OOF')
    replace('README.md','**092（2026-09-27）**','**093（2026-09-27）**')
    replace('README.md','- [最新完整中文论文稿]','093完成精确重复原文折叠与固定预算补证，保持原C48全部信息及来源：自然共同core 88条B/F/A正确76/77/76，压力30条17/16/18；未证明综合升级，停止本版。153次HTTP200，未优惠原价¥4.097118/20，无重试。\n\n- [093报告与历史差异](outputs/093_lossless_evidence_budget/report.md)、[完整指标](outputs/093_lossless_evidence_budget/detailed_tables.md)\n- [最新完整中文论文稿]')
    replace('docs/PROJECT_STATUS.md','092完成）','093完成）')
    replace('docs/PROJECT_STATUS.md','当前研究已完成至092，最新科学结果提交ee8060a2b；实际HEAD可能因后续文档维护变化，以git为准。','当前研究已完成至093；本轮起始HEAD e3999daa6c，实际HEAD以git为准。')
    replace('docs/PROJECT_STATUS.md','|092任务适配|','|093固定预算补证|原文折叠F、补证A与同期B；自然90/压力30，core有效88/30；正确B/F/A为76/77/76及17/16/18|自然A净0、false-S+1；压力净+1、false-S−1；原生救回与最终救回不是同一病例，停止本版|\n|092任务适配|')
    replace('docs/PROJECT_STATUS.md','[092报告]','[093报告](../outputs/093_lossless_evidence_budget/report.md) · [093病例分析](../outputs/093_lossless_evidence_budget/case_analysis.md) · [092报告]')
    replace('docs/PROJECT_STATUS.md','不能再把reserved当未接触holdout；','093用户允许现有全体患者研究；实际在有完整原生D48材料的1401条中冻结120条同期评价，并非9065条全量分类实测。GT只用于分层及评价，不进选证或推理。\n\n不能再把reserved当未接触holdout；')
    replace('docs/PROJECT_STATUS.md','092执行者自检通过、独立审计未执行。','093新增API ¥4.097118/20，153个HTTP200、0重试，无GPU租赁。093与092执行者自检通过，独立审计未执行。')
    replace('docs/TASK_INDEX.md','截至092','截至093')
    replace('docs/TASK_INDEX.md','|---|---|---|---|','|---|---|---|---|\n|093_lossless_evidence_budget|[正式报告](../outputs/093_lossless_evidence_budget/report.md)|未执行；[执行者自检](../outputs/093_lossless_evidence_budget/selfcheck.json)|真实B/F/A首轮完成；停止本版、默认不变，不自动094|')
    replace('docs/RESEARCH_EXECUTION.md','当前092已完成','当前093已完成')
    extra='\n\n作者分层、core无效原因见[补充表](author_strata.md)。两条无效有raw标签，未以旧标签补齐；作者分层不用于新方案选择。\n'
    with (c.OUT/'report.md').open('a',encoding='utf-8',newline='\n') as f:f.write(extra)
    readme='''# 093 已完成：重复原文折叠与固定预算补证

[正式报告](../../outputs/093_lossless_evidence_budget/report.md) · [历史区别](../../outputs/093_lossless_evidence_budget/history_difference.md) · [方法](../../outputs/093_lossless_evidence_budget/method.md) · [病例](../../outputs/093_lossless_evidence_budget/case_analysis.md)

自然90与压力30分报；B/F/A core正确76/77/76（N88）和17/16/18（N30）。停止本版，默认B不变。153次HTTP200、0重试、未优惠原价¥4.097118/20；不自动下一任务。

## 复查与复现

主环境research-verifact-029，通过scripts/run_research.ps1。任务输入/原生回执在忽略目录.local_models/093，仅合法持有数据的本地环境可完整复查；公开哈希不是临床原文替代品。

零API功能检查：`pwsh -NoProfile -File scripts/run_research.ps1 tasks/093_lossless_evidence_budget/test093.py`。

inventory093→build_pool093→prepare093→freeze_execution093是事前冻结链；api093为历史执行器，不是授权再次调用。analyze093→close093→report093→verify093→supplement093→deliver093为结果交付链。结果以独占创建保护，原目录重复分析遇FileExistsError为预期，不删除旧结果绕过保护。重算应复制代码与私有输入到隔离研究副本，保留冻结路径结构，对生成JSON逐值比对；不重新运行API或导航更新脚本。inspect093会在本地显示私有病例，不将终端输出发布。

selfcheck.json是执行者校验，非独立审计。来源源码指纹见source_manifest.json，构造与发送配置分别见main_freeze/execution_freeze；最初盘点版本已在engineering_archive按原SHA保留。解释、作者分层和交付代码是事后分析，不修改冻结候选。
'''
    (c.TASK/'README.md').write_text(readme,encoding='utf-8')
    (c.OUT/'audit_handoff.md').write_text('''# 093 交审说明

独立审计未执行。优先核查：1401原包与历史材料精确一致；F共享表展开等于B；A保留全部B来源、同患者原候选、字符/数量/每note限制；120冻结ID与152物理主请求的别名；153回执预算；raw/core不同分母、两条无效无旧答案填充；自然wrong→wrong导致false-S变化；压力raw救回和final救回ID不同；同患者集中及无重复的不确定性。

主指标调用现行evaluate/paired_compare；另用sklearn和Decimal核查矩阵/PA/MCC/MacroF1及费用，见selfcheck.json。补充递归字段隐私及链接检查见supplement_selfcheck.json。首次隐私扫描将自写decision.reason误认成模型reason字段，已仅对该报告字段作例外并重查通过；没有删除真实模型解释来掩盖泄漏。source_manifest记录历史材料未变。

只发布哈希/ID/指标与抽象病例关系。原临床文本、请求与回执仍在忽略目录，不提交。无独立holdout、无统计等效结论、无全量升级。本轮完成后停止，不恢复092训练、085或094。
''',encoding='utf-8')
    c.put(c.OUT/'completion.json',dict(status='COMPLETE_STOP_VERSION',baseline_head='e3999daa6c7012efcadcd3c2dce641651be3592c',API_cost_cny='4.097118',default_changed=False,independent_audit=False,utc=c.now(),artifacts={p.relative_to(c.ROOT).as_posix():c.sha(p) for folder in [c.TASK,c.OUT] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in str(p)}))
if __name__=='__main__':main()
