"""Synchronize mutable project entries; preserve existing byte-level line endings."""
import common as c


def update(path,replacements,addition=""):
    raw=path.read_bytes()
    newline=b"\r\n" if b"\r\n" in raw else b"\n"
    text=raw.decode("utf-8").replace("\r\n","\n")
    for before,after in replacements:
        assert text.count(before)==1,(path,before)
        text=text.replace(before,after)
    if addition:
        text=text.rstrip()+"\n\n"+addition.strip()+"\n"
    text=text.replace("|\n\n| `008_retrieval_planning`", "|\n| `008_retrieval_planning`")
    path.write_bytes(text.encode("utf-8").replace(b"\n",newline))


if __name__=="__main__":
    update(c.ROOT/"README.md",[
        ("007 已完成上下文辅助检索受控试验与自查，等待独立复核，暂不支持扩大当前版本。最终研究方法和论文贡献点未定。",
         "007 已通过精简独立审计；008 已完成 LLM 检索规划验证与自查，等待独立复核，尚无稳定净收益，优先研究候选融合与证据组织。最终研究方法和论文贡献点未定。"),
        ("| `007_context_retrieval` | 执行分析完成，等待独立复核 |", "| `007_context_retrieval` | 已通过精简独立审计（2026-09-14；见 reviews/007） |"),
        ("审计代码、机器结果、原始文件校验和重复运行验证均已完成。", "| `008_retrieval_planning` | 执行分析与自查完成，等待独立复核 | [任务说明](tasks/008_retrieval_planning/README.md) · [简明中文主报告](outputs/008_retrieval_planning/run_001/report.md) |\n\n审计代码、机器结果、原始文件校验和重复运行验证均已完成。")
        ],"""
## 15. LLM Retrieval Planning

008 在六名新开发患者的 144 条固定 claim 上比较 direct、简单来源扩展和 LLM planner，共用 BM25＋BGE-M3、原 claim rerank 和普通 structured Judge。三臂各 144 条有效预测，311 个实际 Judge 请求（含 12 次无翻转重复），全部服务共 684 次，usage 估算 ¥4.1528＜¥40。Planner−direct 的 ΔMCC 为 LLM +0.0176、human 0，区间均跨 0；100 个计划使用、44 个退回，接口损耗不均衡。20 例完整阅读表明局部证据补充与丢失并存，尚不建议扩大通用 planner，优先检查候选融合/证据覆盖和 Judge 支持边界。阅读 [唯一中文主报告](outputs/008_retrieval_planning/run_001/report.md)；离线重建、费用、79 处锚点和准确交审版本见 [结果入口](outputs/008_retrieval_planning/README.md)。007 的当前独立状态以 [精简审计](reviews/007_context_retrieval.md) 为准，历史报告不回写。
""")
    update(c.ROOT/"AGENTS.md",[
        ("007_context_retrieval 已完成执行、自查，等待独立复核；唯一主报告", "007_context_retrieval 已通过 2026-09-14 精简独立审计，范围与结论见 [reviews/007](reviews/007_context_retrieval.md)；唯一主报告"),
        ("## 之前的研究经验", """## 008 当前成果与后续边界

- 008_retrieval_planning 已完成执行与自查，等待独立复核；唯一主报告为 [report.md](outputs/008_retrieval_planning/run_001/report.md)。执行自查不能替代独立审计，不修改原审计意见或写自己的审计 PASS。
- 使用原开发哈希顺序第 13–18 名 84454、67117、71743、72844、93788、26858，144 条有效 claim（每患者每作者 12）。前 18 名开发患者现已用于方法/案例分析，后续不可称未接触；继续原顺序，不为效果重抽，保留测试不用于调参。
- 三臂 direct/simple/planner 共用 BM25＋BGE-M3 dense、48 候选、原 claim BGE rerank、完整片段 8000 字符上限和 DeepSeek-V4-Flash 普通 structured Judge。原 claim 不改，来源仅辅助查询，不作患者证据；不是原 VeriFact 索引等价复现。完整 body 事前去重，12 次重复只作诊断，不替换 canonical 回答。
- 三臂各 144 条有效预测；planner−direct 的 ΔMCC 为 LLM +0.0176、human 0，患者区间跨 0；与 simple 也无稳定优势。144 个原计划均生成两条查询，100 个使用、44 个按预设退回；LLM 65/72、human 35/72 实际使用，28 个失败仅因空白差异。不能据格式错误推断未理解，也不能静默放宽解析并改写已执行条件。
- 本轮全服务 684 次均一次成功，费用按 usage 估算 ¥4.15278168，未核对账单；无收费预检、失败补跑或余额换号。用户最新长期授权为任务预估总费用 ≤40 元直接执行，已替换未来费用规则；历史 004/006/007 的原授权和 8/16 元预算不回写。
- 20 例完整阅读与 79 处锚点属于执行者诊断，不是新医生 evidence GT。P081/P058 的目标记录已在 direct dense 前 28/39，却被融合后的 48 候选门槛排除；扩展有救回，也有 P080/P128 丢失关键日期记录。优先候选融合、证据覆盖/组织和 Judge 支持边界，暂不扩大通用 planner；不能把正确标签或生成解释当作机制证明。
- 保存的阶段输入、原生回执与代码/配置指纹严格检查；可变 README、AGENTS、审计文档不阻断日常离线重放。当前阅读版本 semantic_003，旧渲染/解释修订快照保留状态。交审 HEAD、未提交修改及文件哈希见 outputs/008_retrieval_planning/handoff_001.json；审计期间停止改动同一批成果。

---

## 之前的研究经验""")])
    print("Updated README/AGENTS; original line endings preserved")
