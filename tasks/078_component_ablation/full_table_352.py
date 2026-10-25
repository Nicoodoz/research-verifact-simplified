"""Offline full same-ID352 table; no new inference or fitted parameters."""
import analyze078 as a
c=a.c
BASE=c.OUT/'f4_extension_001'
OUT=BASE/'full_table_352'
METHODS=['Original','NV','NS_raw','NS_U0','NS_U2','GateA','NS_G','NS_prior','NS_PriorG','NS_StdM','NS_StdV',
         'TV','TS_raw','TS_U0','TS_U2','TS_G','TS_prior','TS_PriorG',
         'F4_raw','F4_U0','F4_U2','F4_G','F4_prior','F4_PriorG']
NAMES=['作者原VeriFact','N-V：非thinking普通判断','N-S：非thinking评分，raw','N-S＋U0','N-S＋U2（原U2基线）',
       'N-S＋U2＋Gate A','N-S＋G','N-S＋仅先验修正','N-S＋PriorG','N-S＋StdM','N-S＋StdV',
       'T-V：thinking普通判断','T-S：thinking评分，raw','T-S＋U0','T-S＋U2','T-S＋G','T-S＋仅先验修正','T-S＋PriorG（当前默认）',
       'F4：thinking评分＋固定四例，raw','F4＋U0','F4＋U2','F4＋G','F4＋仅先验修正','F4＋PriorG']

def main():
    allrows=c.lines(BASE/'predictions.jsonl')
    ids=set(c.read(BASE/'cohort_lists.json')['exclude_actual_example_patients352'])
    rows=[r for r in allrows if r['id'] in ids]
    assert len(rows)==352 and len({r['sid'] for r in rows})==22
    common=set.intersection(*(set(r['methods']) for r in rows))
    assert common==set(METHODS),(common-set(METHODS),set(METHODS)-common)
    table=a.table(rows,METHODS)
    previous={x['method']:x for x in c.read(BASE/'tables.json')['exclude_actual_example_patients352']}
    for m in table:
        if m['method'] in previous:
            for k in ['MCC','PA','AC1','correct','falseS','fallback']:assert m[k]==previous[m['method']][k]
    groups=[]
    for m in METHODS:
        labels=[r['methods'][m]['label'] for r in rows]
        found=next((g for g in groups if g['labels']==labels),None)
        if found is None:groups.append(dict(methods=[m],labels=labels))
        else:found['methods'].append(m)
    equivalence=[g['methods'] for g in groups if len(g['methods'])>1]
    OUT.mkdir(exist_ok=False)
    c.put(OUT/'results.json',dict(n=352,patients=22,rows=table,exact_label_equivalence=equivalence,ids=sorted(ids),new_API_calls=0,new_fits=0))
    text=['# 078完整同队列352条配置表','',
          '22名development患者，已排除实际示例患者；仍有示例候选池重叠。以下24个配置都有完全相同的352条预测。共用原回退规则，非全核心有效子集；不新增API、不重新拟合参数。','',
          'N/T＝非thinking/thinking-high；V＝普通判断；S＝附带三类分数。raw＝原始verdict；U0＝分数最高类；U2＝Supported的log分数加固定2；G＝历史拟合的Supported偏置（不是Gate）；仅先验修正＝冻结类别比例修正；PriorG＝G＋先验修正。Gate A筛选U0→U2的Supported翻转，利用Qwen与患者外模型；StdM/V为标准多类偏置/各类分数缩放加偏置的患者外参照。F4＝T-S加入071固定四例，仍使用旧T-S后处理参数。','',
          '| 实验配置 | MCC | PA | 正确数 | 错误支持数↓ | 回退数 |','|---|---:|---:|---:|---:|---:|']
    for name,m in zip(NAMES,table):
        text.append(f"| {name} | {m['MCC']:.4f} | {m['PA']*100:.2f}% | {m['correct']}/352 | {m['falseS']} | {m['fallback']} |")
    text+=['','逐例标签完全相同的配置组：'+c.canon(equivalence),'',
           '作者证据桥接RN/RT仅覆盖192条中的相应患者子集，动态D4、混合H6、批注R4等也没有全352条预测，因此不能填入本表。它们保留各自同队列比较；本表是078已覆盖352条的全部配置。','',
           '[F4补齐报告](../report.md) · [机器结果](results.json)','']
    with (OUT/'report.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(text))
    files=[OUT/'report.md',OUT/'results.json',c.TASK/'full_table_352.py',BASE/'predictions.jsonl',BASE/'cohort_lists.json']
    c.put(OUT/'manifest.json',dict(status='PASS',all24_methods_same352=True,existing12_rows_match=True,files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in files}))
    print('\n'.join(text))

if __name__=='__main__':main()
