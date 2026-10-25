"""Additive 086 correction; original metrics, receipts and scripts untouched."""
from collections import Counter
from common087 import *

def main():
    old=ROOT/'outputs/086_global_demonstration_selection'
    rows=lines(old/'E_predictions.jsonl');cases=[]
    for x in rows:
        def arm(a):return dict(valid=x['arms'][a]['valid'],raw_verdict=x['arms'][a].get('raw_verdict'),final=x['labels'][a]['PriorG'])
        cases.append(dict(id=x['id'],sid=x['sid'],GT=x['GT'],**attribution(arm('F4_new'),arm('N1_new'),x['GT'])))
    target=next(x for x in rows if x['id']=='9201cd62-ca29-8e71-2111-269e07a43a62')
    receipt=ROOT/target['arms']['F4_new']['receipt_source'];native=json.loads(read(receipt)['transport']['body_text'])
    assert native['choices'][0]['finish_reason']=='length' and not native['choices'][0]['message']['content']
    valid=[x for x in cases if x['both_valid']]
    summary=dict(full_n=len(cases),valid_pair_n=len(valid),system_rescue=sum(x['rescue'] for x in cases),system_harm=sum(x['harm'] for x in cases),
                 valid_rescue=sum(x['rescue'] for x in valid),valid_harm=sum(x['harm'] for x in valid),
                 fallback_rescue=sum(x['rescue'] for x in cases if not x['both_valid']),fallback_harm=sum(x['harm'] for x in cases if not x['both_valid']),
                 valid_raw_rescue=sum(x['raw_rescue'] for x in valid),valid_raw_harm=sum(x['raw_harm'] for x in valid),
                 kind_counts=dict(Counter(x['kind'] for x in cases)),source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in (old/'report.md',old/'E_predictions.jsonl',old/'E_analysis.json',old/'selfcheck.json',receipt)})
    assert (summary['system_rescue'],summary['system_harm'],summary['valid_rescue'],summary['valid_harm'],summary['fallback_rescue'])==(2,3,1,3,1)
    putl(OUT/'086_corrected_attribution.jsonl',cases);put(OUT/'086_correction.json',summary)
    text(OUT/'086_correction.md',f'''# 086机制归因补正（087零API追加）

原086主结果保持：N1相对同期F4为2救回、3伤害、净−1。原报告与所有冻结工件不回写。

复核全部110条，双方核心有效{len(valid)}条：1救回、3伤害；另外1救回涉及F4核心无效/fallback。双方有效时raw正确性没有救回或伤害。归因先处理有效性，再分析raw与最终标签。

病例`9201cd62-ca29-8e71-2111-269e07a43a62`的F4回执finish_reason=length、正文为空，completion_tokens=reasoning_tokens=8192；没有有效raw verdict或scores。系统使用冻结Not Supported回退。N1有效raw为Not Supported，分数10/90/0，经PriorG为Supported。因此这是有效N1与无效F4/fallback的系统差异，不能说两份有效分数跨边界。原mechanism086.py读取valid却未优先分流，并把评价用回退raw当原生raw，导致错误分类。

新函数与合成回归测试位于087，不改原086源码、自检或指标。[全部病例](086_corrected_attribution.jsonl)、[汇总与原工件SHA](086_correction.json)。本补正为执行者核对，不是独立审计。

另澄清：V中F4/N1的S召回相同，N1的NS、NA召回均较高；仅变类别比例、保持这些类内召回，PA优势不会反转。V/E组成差异不能独自解释迁移失败；类内病例差异、样本估计误差和调用波动未被分离。
''')
    print(canonical(summary))

if __name__=='__main__':main()
