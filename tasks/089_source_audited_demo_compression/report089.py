"""Render complete numerical tables; narrative conclusion authored after inspecting results."""
from common089 import *
from collections import Counter

def pct(v):return 'NA' if v is None else f'{100*v:.2f}%'
def table(metrics):
    out=['|配置|MCC|PA|正确数|错误支持数/真实non-S|Macro-F1|S/NS/NA召回|','|---|---:|---:|---:|---:|---:|---|']
    for a,v in metrics.items():out.append(f"|{a}|{v['MCC']:.4f}|{pct(v['PA'])}|{v['correct']}/{v['n']}|{v['false_S']}/{v['non_S']}|{v['Macro_F1']:.4f}|"+' / '.join(pct(v['per_class'][l]['recall']) for l in LABELS)+'|')
    return out
def comparisons(comps):
    out=['|比较|救回/伤害/净值|ΔMCC [95%CI]|ΔPA百分点 [95%CI]|Δ错误支持|患者胜/负/平|等权ΔPA|','|---|---:|---|---|---:|---|---:|']
    for key,x in comps.items():
        m=x['paired']['metrics'];a=m['mcc'];b=m['percent_agreement']
        out.append(f"|{key}|{x['rescue']}/{x['harm']}/{x['net']:+}|{a['delta']:+.4f} [{a['ci95'][0]:+.4f},{a['ci95'][1]:+.4f}]|{100*b['delta']:+.2f} [{100*b['ci95'][0]:+.2f},{100*b['ci95'][1]:+.2f}]|{x['delta_false_S']:+}|{x['patient_wins']}/{x['patient_losses']}/{x['patient_ties']}|{pct(x['patient_equal_delta_PA'])}|")
    return out
def main():
    a=read(OUT/'analysis.json');out=['# 089 完整评价表','','F4原完整四例；P4本轮构造保留原文，与F4共享同体；Q4普通抽取，仅NS示例缩短。Original为同ID作者原VeriFact历史系统，模型/证据不同。混淆矩阵行=医生GT、列=预测，均依S/NS/NA顺序。压力面板S召回无定义；Macro-F1沿固定三类含零支持类，不能与自然面板直接比较。','']
    for panel,d in a['panels'].items():
        out += [f'## {panel}: {d["n"]}条/{d["patients"]}患者，GT {d["GT"]}','','完整系统raw行只在raw缺失时用032 fallback；native raw另表。']
        for m,metrics in d['full_metrics'].items():
            out += ['',f'### 完整分母 {m}','']+table(metrics)+['']+comparisons(d['full_comparisons'][m])+['']
            for arm,v in metrics.items():
                out += [f"**{arm}**：false-S/non-S={pct(v['false_S_rate_nonS'])}；false-S/全部={pct(v['false_S_rate_all'])}；患者等权PA={pct(v['patient_equal_PA'])}。",'', '|类别|Precision|Recall|F1|GT数|预测数|','|---|---:|---:|---:|---:|---:|']
                for l in LABELS:
                    z=v['per_class'][l];out.append(f"|{l}|{pct(z['precision'])}|{pct(z['recall'])}|{pct(z['f1'])}|{z['support']}|{z['predicted']}|")
                out += ['',f"混淆矩阵：`{v['confusion_matrix']}`。",f"患者95%CI：`{v['patient_CI95']}`。",'']
        out += [f"### 三臂共同核心有效 {d['common_core_n']} 条",'']
        for m,metrics in d['common_core_metrics'].items():out += [f'**{m}**','']+table(metrics)+['']+comparisons(d['common_core_comparisons'][m])+['']
        out += [f"### 原生raw自身共同有效 {d['raw_common_n']} 条",'']+table(d['native_raw_metrics'])+['']+comparisons(d['native_raw_comparisons'])+['']
        out += ['### 描述性分层（PriorG）','']
        for name,v in d['strata'].items():out += [f"**{name}**，n={v['n']}，GT={v['GT']}",'']+table(v['metrics'])+['']
    text(OUT/'performance_tables.md','\n'.join(out).rstrip()+'\n')
    records=read(OUT/'construction_summary.json');coverage=read(OUT/'coverage_summary.json');co=['# 来源、构造覆盖与失败台账','','四例主构造与额外候选覆盖分开；模型生成的信息清单不是医生GT。','', '|槽位|臂|状态|原字符|最终字符|初选ID|补回ID|最终ID|','|---|---|---|---:|---:|---|---|---|']
    for r in records:
        for arm in ('P4','Q4'):
            v=r[arm];co.append(f"|{r['ordinal']}|{arm}|{v['status']}|{r['original_chars']}|{v['chars']}|{','.join(v['initial_selected_ids'])}|{','.join(v['added_ids'])}|{','.join(v['selected_ids'])}|")
    co += ['','## 其余8条D候选：不用于替换F4或目标评价','','|候选|臂|状态|原字符|最终字符|初选/最终段数|补回段|','|---|---|---|---:|---:|---|---|']
    for r in coverage['remaining']:
        if r['status']!='constructed':co.append(f"|{r['candidate_id']}|—|{r['status']}|—|—|—|—|");continue
        for arm in ('P4','Q4'):
            v=r[arm];co.append(f"|{r['candidate_id']}|{arm}|{v['status']}|{r['original_chars']}|{len(render_reference(r['source_units'],v['selected_ids']))}|{len(v['initial_selected_ids'])}/{len(v['selected_ids'])}|{','.join(v['added_ids'])}|")
    co+=['','完整模型回答、逐引文的接受/拒绝理由见construction/与coverage/。短/单单元不调用；所有长槽P/Q独立调用，不做目标性能选例。']
    text(OUT/'construction_tables.md','\n'.join(co)+'\n')
    costs=a['cost'];c=['# 089 费用与实际token','','按未优惠原价估算，不是账单对账。F4=P4共享物理调用，逻辑部署费用不能重复加进任务账。','',f"总额¥{costs['total_original_or_unknown_cny']:.8f}/20；构造/核对/覆盖¥{costs['construction_review_coverage_cny']:.8f}/2；尝试{costs['attempts']}，HTTP分布{costs['http_status']}，未知¥{costs['unknown_reserve']:.8f}。",'', '|逻辑臂|输入token|输出token|总token|单独部署同批费用|平均输入|平均输出|core/raw/scores无效数|','|---|---:|---:|---:|---:|---:|---:|---|']
    for arm,v in costs['arms'].items():c.append(f"|{arm}|{v['prompt_tokens']}|{v['completion_tokens']}|{v['total_tokens']}|¥{v['logical_success_original_cny']:.6f}|{v['prompt_distribution']['mean']:.1f}|{v['completion_distribution']['mean']:.1f}|{v['core_invalid']}/{v['raw_invalid']}/{v['scores_invalid']}|")
    f=costs['arms']['F4'];q=costs['arms']['Q4'];c += ['',f"Q相对F输入节省{pct(1-q['prompt_tokens']/f['prompt_tokens'])}；此次输入+输出费用节省{pct(1-q['logical_success_original_cny']/f['logical_success_original_cny'])}。",'',f"构造总额按100/1000/10000例摊销：{costs['amortized_construction_per_case']}元/例。含覆盖检查研究开销，未来复用不需重新构造；检索不因此免费。输出波动和并发时延不是端到端加速证明。",'',f"阶段费用：`{costs['phase_costs']}`。"]
    text(OUT/'cost_tables.md','\n'.join(c)+'\n')
if __name__=='__main__':main()
