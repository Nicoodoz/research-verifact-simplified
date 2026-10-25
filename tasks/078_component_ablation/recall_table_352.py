"""Render saved public-evaluator class recalls; no inference or recalibration."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/078_component_ablation/f4_extension_001/full_table_352'

def main():
    d=json.loads((OUT/'results.json').read_text(encoding='utf-8'))
    labels=['Supported','Not Supported','Not Addressed']
    names=[line.split('|')[1].strip() for line in (OUT/'report.md').read_text(encoding='utf-8').splitlines() if line.startswith('| ')][1:]
    assert len(names)==len(d['rows'])==24
    lines=['# 同352条三类召回率','',
           '召回率＝该类正确识别数÷医生标签属于该类的总数。S=Supported（284条），NS=Not Supported（25条），NA=Not Addressed（43条）。同22名开发患者，沿用完整352条及原回退口径；无新增API。','',
           '| 实验配置 | MCC | PA | S召回率（284条） | NS召回率（25条） | NA召回率（43条） |',
           '|---|---:|---:|---:|---:|---:|']
    for name,r in zip(names,d['rows']):
        cm=r['confusion'];den=[sum(row) for row in cm]
        assert den==[284,25,43]
        vals=[]
        for i,label in enumerate(labels):
            assert abs(cm[i][i]/den[i]-r['recall'][label])<1e-12
            vals.append(f"{r['recall'][label]*100:.2f}%（{cm[i][i]}/{den[i]}）")
        lines.append(f"| {name} | {r['MCC']:.4f} | {r['PA']*100:.2f}% | "+' | '.join(vals)+' |')
    lines+=['',
            'F4 raw相对T-S raw，S/NS/NA正确数分别+3/+1/+1；F4＋PriorG相对T-S＋PriorG分别+5/−2/+1。StdV的NS召回率为0。NS只有25条，每1条对应4个百分点，不把小样本百分点变化直接解释为稳定收益。','',
            '[原完整表](report.md) · [原始机器结果与混淆矩阵](results.json)','']
    with (OUT/'recall_table.md').open('x',encoding='utf-8',newline='\n') as f:f.write('\n'.join(lines))
    print('\n'.join(lines))

if __name__=='__main__':main()
