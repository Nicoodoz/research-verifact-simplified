"""Generate the compact Chinese report from computed artifacts."""
from __future__ import annotations

from collections import Counter
from verifact_research.audit.common import read_csv


def write_report(run, summary, clinicians, ai, comparisons, research, checks):
    matches = Counter(r["status"] for r in comparisons)
    point = [r for r in comparisons if r["part"] == "point"]
    ci = [r for r in comparisons if r["part"].startswith("ci_")]
    main = [r for r in ai if r["publication_role"] == "main"]
    endpoint = [r for r in main if r["author_type"] == "llm" and r["proposition_type"] == "claim" and
                ((r["fact_type"] == "claim" and str(r["top_n"]) == "150") or
                 (r["fact_type"] == "sentence" and str(r["top_n"]) == "100"))]
    select = lambda model, author, kind: next(r for r in main if r["model"] == model and r["author_type"] == author and
                 r["proposition_type"] == kind and r["fact_type"] == "sentence" and str(r["top_n"]) == "100")
    r1 = select("R1-70B", "llm", "claim")
    lines = [
        "# 002：论文核心结果复算与统一评价", "",
        f"本报告由 `{run.name}` 的实际计算结果生成。**已完成 release 预测重评分与评价代码建立；不等于重新生成 BHC、重新检索或重新运行九个 Judge。**", "",
        f"共复算 {summary['configuration_pairs']} 个模型/实验组合（主分析 {summary['main_pairs']}、预分析 {summary['preliminary_pairs']}），处理 {summary['ai_rows']:,} 条实际预测。",
        f"正式论文可明确定位的点估计 {len(point)} 项中，{sum(r['status'] == 'matches_displayed_precision' for r in point)} 项与发表精度一致；CI 端点 {len(ci)} 项中，{sum(r['status'] == 'matches_displayed_precision' for r in ci)} 项一致。这里统计的是逐处数值比对项，包含正文与图重复引用的值。完整结果见 [paper_comparisons.csv](paper_comparisons.csv)，差异保留。", "",
        "## 证据与复算范围", "",
        "- **正式来源**：本地 `docs/sources/VeriFact.pdf`，NEJM AI 3(1), 2026；p6 Table 1、p7 Figure 3、pp6–8 正文。目标数值在计算前录入任务目录 `paper_targets.json`，Figure 3 已对照渲染原图。",
        "- **官方数据定义**：v1.1.0 README 定义三类标签、9 个 Judge、主/预分析矩阵。本报告从原始 CSV/Parquet 重建命题队列及配置连接，并与 001 正式索引/缺失键核对。",
        "- **作者实现证据**：[公开代码固定提交 f115d36](https://github.com/philipchung/verifact/tree/f115d36cb65fa2073fce0a10df56bb37f4cbcd50)。用于核实 bootstrap、排序、端点配置；未执行作者模型或分析脚本，也不把代码当作论文数值。",
        "- **未确认**：正式 Supplementary Appendix 未取得；NEJM 附件访问返回 HTTP403。没有把预印本或推测值当作正式 Table S3。已复算相应 release 矩阵，但不能宣称所有补充表/曲线逐值复现。正文 p9 的四个模型增幅另按作者代码默认场景诊断，结果与解释边界见下文。", "",
        "## 队列与评价定义", "",
        "| 队列 | 全部 | valid only | 患者 |", "| --- | ---: | ---: | ---: |",
    ]
    for author, kind in [("llm", "claim"), ("llm", "sentence"), ("human", "claim"), ("human", "sentence")]:
        all_ = next(r for r in summary["cohorts"] if r["cohort"] == f"{author}_{kind}_all")
        valid = next(r for r in summary["cohorts"] if r["cohort"] == f"{author}_{kind}_valid_only")
        lines.append(f"| {author} / {kind} | {all_['n']:,} | {valid['n']:,} | {all_['patients']} |")
    lines += ["", "**论文复现口径**：保留 invalid，使用原始 `human_gt`；PA/AC1/MCC 均为三分类、命题等权。医生间 PA 是每条命题三个医生对的一致比例再取平均，不是三人一致率，也不是医生与最终 GT 的一致率。Table 1 的标签子集按最初三位医生中至少一位选择该标签定义，子集相互重叠。",
              "", "PA 是 AI 与 GT 完全相同的比例。AC1 使用三类别名义权重与双方/三名医生的合并边际分布。MCC 使用三分类混淆矩阵公式；分母为零时返回 0（与 sklearn 一致），类别 precision/recall 无分母时为 null。固定标签顺序为 Supported、Not Supported、Not Addressed，混淆矩阵行是真值、列是预测。",
              "", f"论文 CI 使用 {summary['bootstrap_iterations']} 次命题有放回抽样、95% percentile 区间、RandomState 种子 0..B−1；按固定作者代码，PA/AC1 先按 proposition_id 排序，MCC 保持 human_verdicts CSV 顺序。AC1 的 bootstrap 单次值按 irrCAC 默认保留 5 位小数。点估计由独立公式计算，并用指定版本库测试。", "",
              "## 医生间一致性：实际复算", "", "| 作者 / 粒度 | n | PA（95% CI） | AC1（95% CI） |", "| --- | ---: | --- | --- |"]
    for r in clinicians:
        if r["subset"] == "all":
            lines.append(f"| {r['author_type']} / {r['proposition_type']} | {r['n']} | {r['percent_agreement']:.1%} ({r['percent_agreement_ci_lower']:.1%}–{r['percent_agreement_ci_upper']:.1%}) | {r['gwet_ac1']:.3f} ({r['gwet_ac1_ci_lower']:.3f}–{r['gwet_ac1_ci_upper']:.3f}) |")
    lines += ["", "全部 16 个分层、各自 n/invalid 数及抽样成员见 `clinician_metrics.csv`、`clinician_subset_membership.csv`。001 已发现的三人各投一类实际为 467，论文流程写 478；此差异未通过修改标签消除。", "",
              "## Figure 3 端点：LLM-written / atomic claim", "",
              "以下均采用 rerank、absolute_time、仅目标住院、deduplicate=True。claim facts 的端点为 N=150，sentence facts 为 N=100；端点是图上标注位置，不代表每条曲线的最大值。", "",
              "| Judge | EHR fact / N | n | PA | AC1 | MCC | 平均输入词数 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for r in sorted(endpoint, key=lambda x: (x["model"], x["fact_type"])):
        lines.append(f"| {r['model']} | {r['fact_type']} / {r['top_n']} | {r['evaluated_n']} | {r['percent_agreement']:.1%} | {r['gwet_ac1']:.3f} | {r['mcc']:.3f} | {r['mean_word_length']:.1f} |")
    lines += ["", f"正文主配置 R1-70B + 100 sentence facts：PA **{r1['percent_agreement']:.2%}**，95% CI {r1['percent_agreement_ci_lower']:.2%}–{r1['percent_agreement_ci_upper']:.2%}；MCC **{r1['mcc']:.4f}**，95% CI {r1['mcc_ci_lower']:.4f}–{r1['mcc_ci_upper']:.4f}。", "",
              "**不能只看 PA 排名**：LLM claim 的 Supported 为 3,274/3,447，“始终预测 Supported”已有 **94.98% PA、MCC=0**，见 `trivial_baseline.csv`。主配置三类 recall 分别约 **96.49%、38.32%、16.67%**。正文所谓 R1-70B “最高 agreement”并非所有模型的 PA 最大值，Figure 3 自己也给出更高的 Gemma PA；应同时报告三类 recall/precision 和 MCC，但这不能替作者修正文义。", "",
              "## 正文关键分层", "", "| Judge | 作者 / 命题 | n | PA | AC1 | MCC |", "| --- | --- | ---: | ---: | ---: | ---: |"]
    for model in ["R1-70B", "Qwen-3-30B-A3B-Thinking"]:
        for author, kind in [("llm", "claim"), ("llm", "sentence"), ("human", "claim")]:
            r = select(model, author, kind)
            lines.append(f"| {model} | {author} / {kind} | {r['evaluated_n']} | {r['percent_agreement']:.1%} | {r['gwet_ac1']:.3f} | {r['mcc']:.3f} |")
    lines += ["", "配置同上，均为 100 sentence facts。human sentence 没有发布 AI 预测，属于矩阵设计未覆盖，不能补出一个模型分数。全部主/预分析与 Top-N 结果见 `ai_metrics.csv`；各类 TP/FP/FN/TN、recall、precision、specificity、NPV、F1 见 `per_class_metrics.csv`。", "",
              "## 差异、边界和实际处理", ""]
    differences = [r for r in comparisons if r["status"] == "differs"]
    lines += ["逐项差异如下（未静默过滤或调整种子来对齐）：", "", "| 来源 / 分层 | 指标 | 论文 | 实际 |", "| --- | --- | ---: | ---: |"]
    for r in differences:
        identity = " / ".join(str(r[k]) for k in ["category", "subset", "model", "author_type", "proposition_type", "fact_type", "top_n"] if k in r)
        lines.append(f"| {identity} | {r['metric']} {r['part']} | {r['paper_value']:.6g} | {r['observed']:.6g} |")
    if not differences:
        lines.append("| 已取得的正式目标 | 无差异 | — | — |")
    lines += ["", "对 R1-70B 主配置另用 sklearn 1.6.1 独立重算每一次 MCC bootstrap，得到相同区间；按作者脚本 5 改为 proposition_id 排序，以及显式 valid-only 口径的诊断见 `mcc_ci_diagnostics.csv`。这些预先列明的变体没有替换主结果，也没有搜索随机种子来匹配论文。当前无法确认正文 MCC 区间差异的原因。", "",
              "### 预分析设置与 p9 模型增幅", "",
              "预分析范围可从 release 确认：LLM claim、N=50、四个 Llama/R1 Judge × 两种 EHR fact。`preliminary_contrasts.csv` 保存单因素配对差值；`preliminary_summary.csv` 的八组合等权平均是本任务的描述性汇总，不冒充论文选参规则。该汇总下 rerank、absolute_time、current admission 的平均 PA 较高，但它们并非每个模型/粒度或每个指标都最高；尤其 current admission 的平均 MCC 为约 0.171，全部住院约 0.174。因此不应把正文概括理解成所有设置均严格占优。", "",
              "作者脚本 9a 的默认场景为 LLM claim、100 sentence facts。四组模型正确/错误的配对表可以从实际预测复算：", "",
              "| 候选 − 对照 | 论文增幅（百分点） | 精确 PA 差（百分点） | 两个单元格分别取一位小数后相减 |", "| --- | ---: | ---: | ---: |"]
    for r in read_csv(run / "model_size_reasoning_contrasts.csv")[1]:
        lines.append(f"| {r['candidate']} − {r['baseline']} | {float(r['paper_percentage_points']):.1f} | {float(r['exact_net_gain_percentage_points']):.4f} | {float(r['separately_rounded_cells_difference_percentage_points']):.1f} |")
    lines += ["", "四个发表数字都能由“候选独有正确率”和“对照独有正确率”各自先按图表精度四舍五入再相减得到，作者代码也确实按这一精度显示单元格。**这提供了一种可检验的解释，但正式 Figure S11 未取得，不能确认作者实际采用了该计算过程。** 后续实验一律用未取整的精确指标相减，最后展示时才取整；不把论文的展示数字当作原始精度结果。"]
    lines += ["", "- **74 条缺失**：全部为 Qwen-3-30B-A3B-Thinking、human claim、claim facts N=100。论文复算显式采用 available 分母 5,574/5,648，保存 `missing_prediction_keys.csv`；其他模型完整，不将其分数假装成同样的分母。`common_available_metrics.csv` 对九个模型在固定共同 5,574 ID 上另算敏感性分析，成员另存。后续默认严格拒绝缺失预测。",
              "- **456 条 invalid**：论文口径全保留，实际 AI 覆盖其中 30 条。`sensitivity_metrics.csv` 对每个配置单列 valid-only 结果，不把 valid-only 冒充原论文。",
              "- **4 名患者时间元数据冲突**：保留全部原标签/预测/输入；另算去掉冲突患者命题的端点敏感性分析，标记在 `cohort_master.csv`。这只衡量这些样本对已有分数的影响，不能证明日期差异导致模型错误，也没有重新过滤 EHR。",
              "- **2 条医生第二轮字段异常**：保持发布的 human_gt，并保留异常标记；均在 human sentence，当前 AI 矩阵无此组，不影响已有 AI 分数。医生 PA/AC1 仅使用第一轮三票。",
              "- **Judge 输入不恒等**：`endpoint_input_comparisons.csv` 对各模型与 R1-70B 的同配置输入做 SHA-256 identity 对比，`ai_metrics.csv` 给出真实输入词数；不同 Judge 的比较是发布系统整体比较，不能直接归因为模型能力。exact text 不同不自动等于医学证据不同。词数严格采用 Python str.split，与作者方法一致；没有声称从图像复原横坐标精确原值。", "",
              "## 后续研究统一口径", "",
              "1. **同一实现**：baseline 和新方法都调用 `verifact_research.evaluation.evaluate`，命令入口 `scripts/evaluate_predictions.py`；不得另写一套指标。主评价三分类、proposition micro PA/AC1/MCC，并给出类别性能。",
              "2. **冻结样本**：使用明确的 cohort CSV 与 SHA-256。建议后续主分析 valid-only，all-propositions 为敏感性分析；LLM claim 为主要复现队列，human claim 与 LLM sentence 分开报告。新拆分单元不能直接继承这些医生标签。",
              "3. **固定 baseline 配置**：采用正文 R1-70B + 100 sentence facts、rerank、absolute_time、current admission、deduplicate=True；不按新方法测试结果逐次挑选 baseline。九个模型的相同 N100 sentence 配置均在 `research_baselines.json/csv` 按相同 valid-only 样本和患者 bootstrap 重评，可作为额外对照。",
              "4. **完整性与公平比较**：默认缺失、重复、非法标签、范围外预测报错；明确记录覆盖和实际 ID。共同可用样本只能作为预先注明的敏感性分析。配对比较用同一患者 bootstrap 抽样，两方法必须覆盖同一队列。",
              "5. **不确定性与数据泄漏**：后续研究使用 1,000 次患者 cluster bootstrap（100 名患者抽样，每名被抽中患者的全部命题随之重复），点估计仍是命题 micro。论文 item bootstrap 仅用于复现。当前仍是全数据描述性 benchmark，尚无训练/验证/测试划分；训练、调参与错误驱动方法开发前必须按 patient 分组冻结划分，避免同患者 BHC/EHR 或 sentence/claim 跨集合。", "",
              "## 可复现入口与文件", "",
              "在项目根目录、Conda `research-verifact` 环境运行：", "", "```powershell", "python -B scripts/reproduce_paper_results.py", "python -B -m unittest discover -s tests -v", "```", "",
              "每次创建新 run，不覆盖历史结果。`manifest.json` 保存输入、代码、依赖、论文及输出 SHA-256；原始数据前后指纹检查结果在 manifest。任务说明和统一评价入口示例见 `tasks/002_reproduce_paper_results/README.md`。", "",
              "`checks.json` 区分程序/关系检查、论文数值差异与未确认来源。已知数据缺陷仍保留；002 完成不会使 001 的 fail 变成 pass。",
    ]
    with (run / "report.md").open("x", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")
