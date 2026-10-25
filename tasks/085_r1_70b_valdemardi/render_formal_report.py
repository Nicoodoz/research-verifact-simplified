"""Render fixed evaluation tables; a human-reviewed decision is appended later."""
from __future__ import annotations

import preflight as p


def fmt(value, digits=4):
    return "—" if value is None else f"{value:.{digits}f}"


def percent(value):
    return "—" if value is None else f"{value * 100:.2f}%"


def main():
    e = p.read(p.PUBLIC / "formal_evaluation.json")
    r = p.read(p.PUBLIC / "formal_reconciliation.json")
    s = p.read(p.PUBLIC / "formal_selfcheck.json")
    arms = ("Original-VeriFact", "V4-B", "V4-F4", "R1-B", "R1-F4")
    lines = ["# 085 Valdemardi R1-70B正式受控Judge替换：中文报告", "",
             "## 范围与完整性", "",
             f"冻结084的180条/21名已暴露development患者，同ID B/F4各180个请求。R1共360个首次HTTP200：原Stage B三条复用、本轮新增357条。全部请求只改变Judge模型；V4-B/F4复用084原结果，不重调。评价GT在360个R1 HTTP200后读取。主要比较用最终content中的raw verdict，reasoning_content只存档。共同有效{e['common_valid_n']}/180条、{e['common_valid_patients']}患者；无效/排除{len(e['excluded_from_common'])}条，不插补。", "",
             "实际服务名为Valdemardi/DeepSeek-R1-Distill-Llama-70B-AWQ；它与原Casperhansen目标同为R1-Distill-Llama-70B家族、公开AWQ配置相同，但不是同一仓库checkpoint，也不是原VeriFact完整流水线的逐字节复现。远端权重字节与运行版本未由本机独立取证。默认C48→V4 T-S→Frozen PriorG未改；不使用reserved40。", "",
             "## Raw主结果", "",
             "所有下表配置在同一共同有效ID上比较。`Original-VeriFact`为作者原结果；V4-B/F4为084缓存，R1-B/F4为本次实测。MCC和PA按项目统一口径，false-S的分母为GT非Supported。", "",
             "|配置|MCC|PA|正确数|错误支持数|Gwet AC1|Macro-F1|", "|---|---:|---:|---:|---:|---:|---:|"]
    for arm in arms:
        x = e["primary"][arm]
        lines.append(f"|{arm}|{fmt(x['MCC'])}|{percent(x['PA'])}|{x['correct']}/{x['n']}|{x['false_S']}/{x['non_S']}|{fmt(x['AC1'])}|{fmt(x['macro_F1'])}|")
    lines += ["", "## 同ID配对差值", "",
              "|比较（候选−基线）|救回|伤害|净正确|ΔPA [95%患者CI]|ΔMCC [95%患者CI]|患者胜/负/平|",
              "|---|---:|---:|---:|---|---|---:|"]
    for name, x in e["comparisons"].items():
        paired = x["candidate_minus_baseline"]["metrics"]
        pa = paired["percent_agreement"]
        mcc = paired["mcc"]
        lines.append(f"|{name}|{len(x['rescued_ids'])}|{len(x['harmed_ids'])}|{x['net_correct']:+d}|{percent(pa['delta'])} [{percent(pa['ci95'][0])}, {percent(pa['ci95'][1])}]|{fmt(mcc['delta'])} [{fmt(mcc['ci95'][0])}, {fmt(mcc['ci95'][1])}]|{x['patient_wins']}/{x['patient_losses']}/{x['patient_ties']}|")
    effect = e["F4_cross_model_effect"]
    lines += ["", f"F4效应的跨Judge差（R1的F4−B减去V4的F4−B）：ΔPA {percent(effect['delta_PA_effect_difference'])}，患者bootstrap 95%区间[{percent(effect['patient_bootstrap_CI95'][0])}, {percent(effect['patient_bootstrap_CI95'][1])}]。所有配对CI按患者整组重抽1000次，种子0..999；这是已暴露development上的不确定性描述。", "",
              "## 三类表现与风险", "",
              "|配置|GT类别|支持数|预测数|P|R|F1|", "|---|---|---:|---:|---:|---:|---:|"]
    for arm in arms:
        for label in p.LABELS:
            x = e["primary"][arm]["per_class"][label]
            lines.append(f"|{arm}|{label}|{x['support']}|{x['predicted']}|{percent(x['precision'])}|{percent(x['recall'])}|{percent(x['f1'])}|")
    lines += ["", "混淆矩阵每行按GT、每列按预测，顺序均为S/NS/NA：", ""]
    for arm in arms:
        lines.append(f"- {arm}: `{e['primary'][arm]['confusion_matrix']}`")
    lines += ["", "## Frozen PriorG及分数兼容性（次要）", "",
              f"B/F4两臂同时有真实有效三类`label_scores`的共同样本：{e['secondary_score_valid_pair_n']}/{e['common_valid_n']}。只在这些样本上比较R1 raw、U0、U2和V4训练时冻结的PriorG；没有重拟合R1校准。", "",
              "|配置|MCC|PA|正确数|错误支持数|Gwet AC1|Macro-F1|", "|---|---:|---:|---:|---:|---:|---:|"]
    for arm, x in e["secondary"].items():
        lines.append(f"|{arm}|{fmt(x['MCC'])}|{percent(x['PA'])}|{x['correct']}/{x['n']}|{x['false_S']}/{x['non_S']}|{fmt(x['AC1'])}|{fmt(x['macro_F1'])}|")
    lines += ["", "## 患者分布", "",
              "|患者ID|例数|原VeriFact正确|V4-B|V4-F4|R1-B|R1-F4|",
              "|---|---:|---:|---:|---:|---:|---:|"]
    for sid, x in e["patient_results"].items():
        lines.append(f"|{sid}|{x['n']}|{x['Original-VeriFact']}|{x['V4-B']}|{x['V4-F4']}|{x['R1-B']}|{x['R1-F4']}|")
    lines += ["", "## 运行与费用", "",
              f"冻结360位置均有唯一HTTP200；原B三条、本轮formal 357条。共{r['total_attempts']}次正式位置请求、{r['retries']}次额外尝试、{r['unknown_outcomes']}个未知结果。B/F4输入token合计{r['B_prompt_tokens']}/{r['F4_prompt_tokens']}，输出token合计{r['B_completion_tokens']}/{r['F4_completion_tokens']}；成功请求耗时和{r['successful_request_seconds_sum']/3600:.2f}小时，最长单请求{r['longest_request_seconds']:.1f}秒。该耗时和不等于实例计费时长。", "",
              "本实例真实时价及完整开机占用时长未提供，GPU租金金额不可可靠计算；本地vLLM没有单独按请求API账单，不据此宣称免费，也不套用历史时价。请求与费用台账见`formal_reconciliation.json`及`formal_request_ledger.jsonl`。", "",
              "## 自检与证据限制", "",
              f"执行者自检{s['n_checks']}项PASS，独立审计未执行。回执与请求SHA、模型名、输入token、20K预算、唯一HTTP200及同ID评价均可回查；raw原文与原生回执保留在仓库忽略的私有目录，公开只保存ID/哈希/汇总。点估计用sklearn独立复核，bootstrap复用项目统一实现。", "",
              "本队列为已暴露development，21名患者且F4示例池曾与部分评价患者重叠；不能称新最终患者外测试或原VeriFact全系统复现。单次R1输出不证明稳定重测效果。Frozen PriorG在V4上开发，其R1结果仅是兼容性分析；raw收益不能直接视为当前最终系统升级。", "",
              "## 研究决定", "",
              "（根据完整结果、自检和类别风险填写；不事后修改选择标准。）", ""]
    path = p.PUBLIC / "report_formal.md"
    if path.exists():
        raise FileExistsError("report already exists")
    p.put(path, "\n".join(lines).encode("utf-8"))
    print(path)


if __name__ == "__main__":
    main()
