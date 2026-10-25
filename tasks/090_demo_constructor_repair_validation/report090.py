"""Source-free complete tables and morning report from frozen outcomes."""
from common090 import *
sys.path.insert(0,str(ROOT/'tasks/089_source_audited_demo_compression'))
from report089 import table,comparisons,pct
def main():
    a=read(PUB/'analysis.json');out=['# 090 双面板完整数表','','B无示例，F4原完整四例，P90最终第2工程版信息覆盖抽取，Q90独立普通抽取。Original为同ID作者原VeriFact不同模型/证据历史参照。所有矩阵行GT、列预测，顺序S/NS/NA。固定三类Macro-F1含压力集零支持S类，不跨面板比较。','']
    for panel,d in a['panels'].items():
        out += [f"## {panel}：{d['n']}条/{d['patients']}患者，GT={d['GT']}",'']
        for method,metrics in d['full_metrics'].items():
            out += [f'### 完整分母 {method}','']+table(metrics)+['']+comparisons(d['full_comparisons'][method])+['']
            for arm,v in metrics.items():
                out += [f"**{arm}**：false-S/non-S={pct(v['false_S_rate_nonS'])}，false-S/全部={pct(v['false_S_rate_all'])}，患者等权PA={pct(v['patient_equal_PA'])}。",'','|类别|Precision|Recall|F1|GT数|预测数|','|---|---:|---:|---:|---:|---:|']
                for l in LABELS:
                    z=v['per_class'][l];out.append(f"|{l}|{pct(z['precision'])}|{pct(z['recall'])}|{pct(z['f1'])}|{z['support']}|{z['predicted']}|")
                out += ['',f"混淆矩阵：`{v['confusion_matrix']}`。",f"患者95%CI：`{v['patient_CI95']}`。",'']
        out += [f"### 三臂/四臂共同核心有效：{d['common_core_n']}条",'']
        for m,metrics in d['common_core_metrics'].items():out += [f'**{m}**','']+table(metrics)+['']+comparisons(d['common_core_comparisons'][m])+['']
        out += [f"### 原生raw共同有效：{d['raw_common_n']}条",'']+table(d['native_raw_metrics'])+['']+comparisons(d['native_raw_comparisons'])+['']
        out += ['### 描述性分层：PriorG','']
        for k,v in d['strata'].items():out += [f"**{k}**，n={v['n']}，GT={v['GT']}",'']+table(v['metrics'])+['']
    text(PUB/'performance_tables.md','\n'.join(out).rstrip()+'\n')
    cost=a['cost'];c=['# 090 原价账本与token','','全部收费阶段及未知预留累计，不结转历史余额、不用优惠扩大预算。','',
      f"总额¥{cost['total_original_or_unknown_cny']:.8f}/40；构造/技术测试/核对¥{cost['construction_review_coverage_cny']:.8f}/4；尝试{cost['attempts']}，HTTP分布{cost['http_status']}，未知预留¥{cost['unknown_reserve']:.8f}。",'',
      '|臂|输入token|输出token|总token|成功调用原价|平均输入|平均输出|core/raw/scores无效|','|---|---:|---:|---:|---:|---:|---:|---|']
    for arm,v in cost['arms'].items():c.append(f"|{arm}|{v['prompt_tokens']}|{v['completion_tokens']}|{v['total_tokens']}|¥{v['logical_success_original_cny']:.6f}|{v['prompt_distribution']['mean']:.1f}|{v['completion_distribution']['mean']:.1f}|{v['core_invalid']}/{v['raw_invalid']}/{v['scores_invalid']}|")
    f=cost['arms']['F4']
    for arm in ('P90','Q90'):
        if arm not in cost['arms']:continue
        v=cost['arms'][arm];c+=['',f"{arm}相对F4：输入节省{pct(1-v['prompt_tokens']/f['prompt_tokens'])}，本轮成功推理费用节省{pct(1-v['logical_success_original_cny']/f['logical_success_original_cny'])}。"]
    c += ['', '|臂|平均请求秒|中位秒|P95秒|最大秒|', '|---|---:|---:|---:|---:|']
    for arm,v in cost['arms'].items():
        d=v['elapsed_seconds_distribution'];c.append(f"|{arm}|{d['mean']:.2f}|{d['median']:.2f}|{d['p95']:.2f}|{d['max']:.2f}|")
    c+=['',f"一次性构造/测试/核对摊销：{cost['amortized_construction_per_case']}元/例（100/1000/10000例）。阶段原价：`{cost['phase_costs']}`。",'',
        '实际请求时长分布保留在cost_ledger.json；并发请求时延不等于整篇核验端到端时间，输出含thinking。费用是usage原价估算，不是账单对账。']
    text(PUB/'cost_tables.md','\n'.join(c)+'\n')
    n=a['panels']['natural'];p=a['panels']['pressure'];brief=['# 明早简报：090实测','','工程修复产生了P90与独立Q90，已完成冻结四臂同批比较。两个面板分别解释，不能相加为自然PA。','', '## 自然主面板','']+table(n['full_metrics']['PriorG'])+['']+comparisons(n['full_comparisons']['PriorG'])+['','## NS/NA压力面板','']+table(p['full_metrics']['PriorG'])+['']+comparisons(p['full_comparisons']['PriorG'])+['',f"总原价及未知预留¥{cost['total_original_or_unknown_cny']:.8f}/40。研究判断见report.md，全部类别风险见performance_tables.md。085/AutoDL/AWS/R1、本地8000/18000服务未访问，不自动091。"]
    text(PUB/'morning_brief.md','\n'.join(brief)+'\n')
if __name__=='__main__':main()
