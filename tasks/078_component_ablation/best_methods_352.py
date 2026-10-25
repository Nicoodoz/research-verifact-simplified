"""Same352 multi-metric comparison, using the public evaluator and cached predictions."""
import analyze078 as a
c=a.c
BASE=c.OUT/'f4_extension_001'
METHODS=['Original','TS_PriorG','F4_PriorG','F4_U2','F4_raw','NS_prior','NS_StdM','NS_StdV']
NAMES=['原VeriFact','无示例T-S＋PriorG','F4＋PriorG','F4＋U2','F4原始判断','非thinking＋仅先验修正','非thinking＋StdM','非thinking＋StdV']

def main():
    ids=set(c.read(BASE/'cohort_lists.json')['exclude_actual_example_patients352'])
    rows=[r for r in c.lines(BASE/'predictions.jsonl') if r['id'] in ids]
    assert len(rows)==352
    metrics=[]
    for method,name in zip(METHODS,NAMES):
        e=a.evaluate(a.cohort(rows),a.prediction(rows,method),profile='none',missing='error')
        m=a.metrics(rows,method)
        m.update(name=name,per_class=e['per_class'],macro_F1=sum(e['per_class'][k]['f1'] or 0 for k in a.LABELS)/3,
                 balanced_accuracy=sum(e['per_class'][k]['recall'] for k in a.LABELS)/3,
                 false_supported_rate=m['falseS']/68)
        metrics.append(m)
    pairs=[a.pair(rows,'Original',m) for m in METHODS[1:]]
    out=BASE/'best_methods_352';out.mkdir(exist_ok=False)
    c.put(out/'results.json',dict(n=352,patients=22,class_counts=dict(zip(a.LABELS,[284,25,43])),methods=metrics,comparisons_to_original=pairs,new_API_calls=0,
        selection='Descriptive shortlist chosen after observing078 results: current default, F4 candidates and strong nonthinking references; not a new winner-selection test.'))
    s=['# 352条主要方法与原VeriFact多指标比较','',
       '同22名开发患者、352条命题，S/NS/NA=284/25/43；已排除实际示例所属患者，但仍有教学候选池重叠。事后挑选有代表性的主要配置展示，不是新的独立最终确认。所有原预测、回退与后处理参数不变；无新增API。','',
       'T-S=thinking-high评分；F4=T-S加入固定四例；PriorG=冻结G与类别比例修正；U2=固定λ2；StdM/V=患者外标准校准参照。非thinking方法与原作者具有不同推理/训练预算，本表是同ID系统比较，不是等资源实验。','',
       'PA是正确率；AC1是校正随机一致性的指标；Macro-F1对三类F1等权平均；平衡准确率对三类召回率等权平均。错误支持率以实际非S的68条为分母，不等于1−S精确率。','',
       '| 配置 | MCC | PA | AC1 | Macro-F1 | 平衡准确率 | 正确数 | 错误支持数/68 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for m in metrics:s.append(f"| {m['name']} | {m['MCC']:.4f} | {m['PA']*100:.2f}% | {m['AC1']:.4f} | {m['macro_F1']*100:.2f}% | {m['balanced_accuracy']*100:.2f}% | {m['correct']}/352 | {m['falseS']}（{m['false_supported_rate']*100:.2f}%） |")
    s+=['','## 每类精确率/召回率/F1','',
        '精确率：判成该类的病例中多少是真的；召回率：实际该类病例中识别对多少；F1综合精确率与召回率。每格按P/R/F1顺序，均为百分比。','',
        '| 配置 | S：P/R/F1 | NS：P/R/F1 | NA：P/R/F1 |','|---|---:|---:|---:|']
    for m in metrics:
        vals=[' / '.join(f"{(m['per_class'][k][z] or 0)*100:.2f}" for z in ['precision','recall','f1']) for k in a.LABELS]
        s.append('| '+m['name']+' | '+' | '.join(vals)+' |')
    s+=['','## 相对原VeriFact的配对比较','',
        '1000次患者cluster bootstrap；以下为各配置相对原系统，未经多重比较校正。PA单位为百分点。','',
        '| 配置 | 净正确 | ΔPA [95%区间] | ΔMCC [95%区间] | 错误支持变化 |','|---|---:|---:|---:|---:|']
    for name,p in zip(NAMES[1:],pairs):
        pa=p['metrics']['percent_agreement'];mc=p['metrics']['mcc']
        s.append(f"| {name} | {p['net']:+d} | {pa['delta']*100:+.2f} [{pa['ci95'][0]*100:+.2f}, {pa['ci95'][1]*100:+.2f}] | {mc['delta']:+.4f} [{mc['ci95'][0]:+.4f}, {mc['ci95'][1]:+.4f}] | {p['delta_falseS']:+d} |")
    s+=['','当前默认和所有F4行均含6条原定回退；其余表内方法为0。已保存各类混淆矩阵、召回分母、Judge估算成本与全部配对结果；原作者实际调用成本不可得，不作等成本结论。','',
        '[机器结果](results.json) · [24配置完整表](../full_table_352/report.md) · [F4补齐报告](../report.md)','']
    with (out/'report.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(s))
    c.put(out/'manifest.json',dict(status='PASS',files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [out/'report.md',out/'results.json',BASE/'predictions.jsonl',c.TASK/'best_methods_352.py']}))
    print('\n'.join(s))

if __name__=='__main__':main()
