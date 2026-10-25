"""Readable complete fixed tables, generated from analysis without inference."""
from common087 import *
import analyze087 as a

def main():
    q=read(OUT/'analysis.json');c=q['cost']
    out=['# 087完整评价表\n\n所有区间均为1000次患者配对bootstrap的探索性95%区间，未校正多重比较，不覆盖调用的全部随机性。混淆矩阵真实行、预测列，固定S/NS/NA顺序。\n']
    for title,key in [('完整110条（raw包含事前fallback，不冒充全原生raw）','full_metrics'),(f"四臂共同核心有效{q['common_core_n']}条",'common_core_metrics')]:
        out.append(f'\n## {title}\n')
        for m in METHODS:
            out.append(f'\n### {m}\n\n|实验配置|MCC|PA|正确数|错误支持/nonS|错误支持/全体|Macro-F1|患者等权PA|\n|---|---:|---:|---:|---:|---:|---:|---:|\n')
            for arm,x in q[key][m].items():
                out.append(f"|{arm}|{x['MCC']:.4f}|{x['PA']:.2%}|{x['correct']}/{x['n']}|{x['false_S']}/{x['non_S']} ({x['false_S_rate_nonS']:.2%})|{x['false_S_rate_all']:.2%}|{x['Macro_F1']:.4f}|{x['patient_equal_PA']:.2%}|\n")
            out.append('\n|配置|S P/R/F1|NS P/R/F1|NA P/R/F1|混淆矩阵|\n|---|---|---|---|---|\n')
            for arm,x in q[key][m].items():
                fmt=lambda v:'NA' if v is None else f'{v:.4f}'
                cells=['/'.join(fmt(x['per_class'][k][z]) for z in ('precision','recall','f1')) for k in LABELS]
                out.append('|'+arm+'|'+'|'.join(cells)+'|`'+canonical(x['confusion_matrix'])+'`|\n')
    for title,key in [('完整分母','full_comparisons'),('共同核心有效','common_core_comparisons')]:
        out.append(f'\n## {title}固定配对（候选减对照）\n')
        for m in METHODS:
            out.append(f'\n### {m}\n\n|比较|救回/伤害/净值|ΔMCC [95%CI]|ΔPA百分点 [95%CI]|Δ错误支持|患者胜/负/平|等权PA差百分点|\n|---|---:|---|---|---:|---|---:|\n')
            for key2,x in q[key][m].items():
                met=x['paired']['metrics'];mc=met['mcc'];pa=met['percent_agreement']
                out.append(f"|{key2}|{x['rescue']}/{x['harm']}/{x['net']:+d}|{mc['delta']:+.4f} [{mc['ci95'][0]:+.4f},{mc['ci95'][1]:+.4f}]|{100*pa['delta']:+.2f} [{100*pa['ci95'][0]:+.2f},{100*pa['ci95'][1]:+.2f}]|{x['delta_false_S']:+d}|{x['patient_wins']}/{x['patient_losses']}/{x['patient_ties']}|{100*x['patient_equal_delta_PA']:+.2f}|\n")
    out.append('\n## 完整分母最终变化归因\n\n|比较|类别|病例数|救回|伤害|\n|---|---|---:|---:|---:|\n')
    for key,groups in q['attribution_summary'].items():
        for kind,x in groups.items():out.append(f"|{key}|{kind}|{x['n']}|{x['rescue']}|{x['harm']}|\n")
    out.append('\n## 作者与暴露分层（描述性）\n\n分层不重新选赢家；分层raw若含fallback仍为系统完整分母口径。详细原生共同有效与逐患者数据见analysis.json。\n')
    for key,z in q['strata'].items():
        out.append(f"\n### {key}：{z['n']}条/{z['patients']}患者，GT {z['GT']}\n\n|层|配置|MCC|PA|正确|false-S/nonS|NS召回|NA召回|\n|---|---|---:|---:|---:|---:|---:|---:|\n")
        for m,arms in z['metrics'].items():
            for arm,x in arms.items():
                ns=x['per_class']['Not Supported']['recall'];na=x['per_class']['Not Addressed']['recall']
                fmt=lambda v:'NA' if v is None else f'{v:.2%}'
                out.append(f"|{m}|{arm}|{x['MCC']:.4f}|{x['PA']:.2%}|{x['correct']}|{x['false_S']}/{x['non_S']}|{fmt(ns)}|{fmt(na)}|\n")
    text(OUT/'performance_tables.md',''.join(out))
    s=['# 087 token、成本与时长\n\n原价输入3、输出9元/百万token；不扣缓存/闲时折扣。时长为本次并发客户端观测，不能证明端到端加速。\n\n|臂|输入token|输出token|总token|累计成功原价¥|每例¥|截断/110|核心无效/110|\n|---|---:|---:|---:|---:|---:|---:|---:|\n']
    for arm,x in c['arms'].items():s.append(f"|{arm}|{x['prompt_tokens']}|{x['completion_tokens']}|{x['total_tokens']}|{x['original_success_cny']:.6f}|{x['original_success_per_case_cny']:.6f}|{x['truncation_n']}|{x['core_invalid']}|\n")
    s.append('\n|臂|变量|均值|min|P25|中位数|P75|P95|max|\n|---|---|---:|---:|---:|---:|---:|---:|---:|\n')
    for arm,x in c['arms'].items():
        for key in ('prompt_distribution','completion_distribution','total_distribution','elapsed_seconds_distribution'):
            z=x[key];s.append('|'+arm+'|'+key+'|'+ '|'.join(f"{z[k]:.2f}" for k in ('mean','min','p25','median','p75','p95','max'))+'|\n')
    s.append(f"\nCL4相对F4输入token减少{c['CL4_vs_F4_prompt_reduction']:.2%}，成功调用总原价减少{c['CL4_vs_F4_original_cost_reduction']:.2%}。全部尝试及未知预留¥{c['total_original_or_unknown_cny']:.6f}/20；未知预留¥{c['unknown_reserved_cny']:.6f}。\n")
    text(OUT/'cost_tables.md',''.join(s))
    print(canonical(dict(status='tables_written')))

if __name__=='__main__':main()
