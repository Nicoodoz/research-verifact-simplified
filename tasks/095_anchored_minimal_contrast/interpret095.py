"""Explain final frozen output paths and strata without fitting or new calls."""
from collections import Counter
import common095 as c

LABELS=['Supported','Not Supported','Not Addressed']

def main():
    bm=c.read(c.OUT/'baseline_metrics.json')['common_core'];pairs=c.read(c.OUT/'baseline_paired.json');strata=c.read(c.OUT/'baseline_strata.json');diag=c.read(c.OUT/'decision_boundary_diagnosis.json');rep=c.read(c.OUT/'repeat_analysis.json');rows=c.lines(c.OUT/'unified_9065_predictions.jsonl')
    a,b,raw=(bm[k] for k in ['Original','B_PriorG','B_raw']);p=pairs['B_PriorG-Original'];g=pairs['B_PriorG-B_raw']
    out=['# 095 全量同ID结果的解释','','本页只描述冻结预测、分数及可观测转移，不选择新的阈值、样本或方案。所有主比较使用共同core集合；历史重复另用自身共同有效分母。','','## 系统位置与类别代价','',f"同ID原作者→B＋G：PA {a['PA']:.2%}→{b['PA']:.2%}，MCC {a['MCC']:.4f}→{b['MCC']:.4f}，Macro-F1 {a['Macro_F1']:.4f}→{b['Macro_F1']:.4f}，false-S {a['false_S']}→{b['false_S']}。预测S中的错误比例分别为{a['false_discovery_S']:.2%}和{b['false_discovery_S']:.2%}。这些量衡量不同取舍，不把一个总体分数代表全部类别。",'', '|真实类别|原作者召回|B raw召回|B＋G召回|B＋G相对作者救回/伤害|raw→G救回/伤害|','|---|---:|---:|---:|---:|---:|']
    for i,lab in enumerate(LABELS):
        out.append(f"|{lab}|{a['recall'][i]:.2%}|{raw['recall'][i]:.2%}|{b['recall'][i]:.2%}|{p['rescue_by_GT'][lab]}/{p['harm_by_GT'][lab]}|{g['rescue_by_GT'][lab]}/{g['harm_by_GT'][lab]}|")
    out+=['','## 原生输出与分数映射','',f"raw与U0定义不同，但在本次{diag['N']}条core有效回答中有{diag['raw_U0_disagreement']}条不同；若差异为0，只能说本队列逐例一致，不能包装为两个独立有效组件。raw→G的路径为："+'；'.join(f'{k}={v}' for k,v in diag['raw_to_G_paths'].items())+'。', '',f"同一份证据与回答经G映射，新增错误支持{g['false_S_added']}、避免{g['false_S_prevented']}。这可确定归因于决策映射；不能推断模型阅读了新的信息，或把分数跨界当作关系理解改善。",'', '最常见的自报三分数组合如下。表中同一评分可能对应不同GT和原生标签，是开发数据的描述，不据此重新拟合。','','|自报S/NS/NA分数|N|患者数|raw正确|G正确|G错误支持|','|---|---:|---:|---:|---:|---:|']
    for z in diag['score_profiles_by_frequency'][:8]:
        out.append(f"|{z['scores_S_NS_NA']}|{z['N']}|{z['patients']}|{z['raw_correct']}|{z['final_correct']}|{z['false_S']}|")
    out+=['','## 患者和来源分布','',f"B＋G相对作者的患者胜/负/平为{p['patient_win_loss_tie']}；存在救回的患者{p['rescue_patients']}名。各患者命题数不同，胜负平不取代micro指标；病例聚集也不能单凭净正确判断原因。",'']
    pos=sorted([(sid,n) for sid,n in p['patient_net'].items() if n>0],key=lambda z:(-z[1],z[0]));neg=sorted([(sid,n) for sid,n in p['patient_net'].items() if n<0],key=lambda z:(z[1],z[0]))
    out+=['正净变化最多的5名患者：'+str(pos[:5])+'；负净变化最大的5名患者：'+str(neg[:5])+'。','']
    for field,title in [('author','命题作者类型'),('C48_source','实际证据来源'),('initial_cache_vs_new','历史缓存与本轮补齐')]:
        out+=['### '+title,'','|层|N|作者/B＋G正确|作者/B＋G MCC|作者/B＋G false-S|','|---|---:|---:|---:|---:|']
        for key,t in strata.get(field,{}).items():
            x,y=t['Original'],t['B_PriorG'];out.append(f"|{key}|{x['N']}|{x['correct']}/{y['correct']}|{x['MCC']:.4f}/{y['MCC']:.4f}|{x['false_S']}/{y['false_S']}|")
        out.append('')
    out+=['这些层的患者、类别和材料组成不同，来源和批次没有随机分配。不能把本地BGE层与API层的差值解释为检索实现因果效果，也不能用新旧缓存层直接估计服务漂移。所有新增B只补缺失，没有按成绩替换原来选中的成功回答。','','## 既有重复能说明什么','']
    for method,z in rep['existing'].items():
        if not z['N']:out.append(f'- {method}没有可评价的共同有效重复。');continue
        q=z['paired'];out.append(f"- {method}：历史最早/最晚共同有效{z['N']}条，标签改变{z['label_changes']}条，后者相对前者救回/伤害{q['rescue']}/{q['harm']}，净{q['net']:+d}，患者胜/负/平{q['patient_win_loss_tie']}。")
    out+=['','这是现有被选择过的重复子集，只表明固定请求仍可能改变输出，不估计任意新病例的波动率。本轮没有另加收费重复或候选阶段批次桥接，因此不能排除大表中的未测批次效应。','','## 无效回答和主张范围','']
    invalid=[r for r in rows if r['B_present'] and not r['B_core_valid']];reasons=Counter(str(r['B']['parsed'].get('finish_reason')) for r in invalid);out.append(f"成功但core无效{len(invalid)}条，按原GT计数{dict(Counter(r['GT'] for r in invalid))}，finish_reason为{dict(reasons)}。它们保留在9065行总表，未被赋予其他模型标签，也未因无效重发。")
    out+=['','B的质量优势若存在，属于当前冻结系统的开发阶段同ID比较。095对比候选没有最终分类输出，其构造缺陷不提供C−B或C−E的分类效应估计。研究可收束为系统、边界和来源约束的实证结果，不能将现有B优势转换为新增算法贡献。','', '[统一表](unified_9065_predictions.jsonl) · [完整类别路径](decision_boundary_diagnosis.json) · [配对区间](baseline_paired.json) · [病例来源解释](baseline_cases.md)']
    with (c.OUT/'baseline_findings.md').open('w',encoding='utf-8',newline='\n') as f:f.write('\n'.join(out)+'\n')
    print('Frozen baseline interpretation written')

if __name__=='__main__':main()
