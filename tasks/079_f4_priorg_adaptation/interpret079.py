"""Record descriptive decision after fixed analysis; no search or fitting."""
from collections import Counter
import common079 as c

def main():
    rows=c.lines(c.OUT/'predictions.jsonl')
    changed=[dict(id=x['id'],sid=x['sid'],GT=x['GT'],scores=x['arms']['F4']['scores'],old=x['methods']['F4_PriorG']['label'],new=x['methods']['F4_newPriorG']['label']) for x in rows if x['methods']['F4_PriorG']['label']!=x['methods']['F4_newPriorG']['label']]
    assert len(changed)==5 and all(x['old']=='Supported' and x['new']=='Not Supported' for x in changed)
    assert Counter(x['GT'] for x in changed)=={'Supported':4,'Not Supported':1}
    collision=[x for x in changed if x['scores']=={'Supported':10,'Not Supported':85,'Not Addressed':5}]
    assert len(collision)==4 and Counter(x['GT'] for x in collision)=={'Supported':3,'Not Supported':1}
    c.put(c.OUT/'changed_case_diagnosis.json',dict(cases=changed,identical_score_collision_ids=[x['id'] for x in collision],
        scope='Post-analysis descriptive diagnosis of five precomputed label changes; no new method, threshold selection, or extra clinician labels.'))
    text=('**本次未支持“为F4重新拟合简单PriorG就能兑现额外收益”。停止本版本的单参数G适配，不升级默认，不追加阈值/正则/校准器搜索。**\n\n'
          'F4新PriorG相对F4旧PriorG，352条仅改判5条，全部S→NS：救回1条NS、伤害4条S，正确298→295，MCC0.5771→0.5689，错误支持12→11；NS召回36%→40%，S召回90.49%→89.08%，NA召回保持74.42%。Macro-F1从64.2039%到64.2263%，仅+0.0224个百分点，不能据这一微小变化宣称整体升级。PA/MCC差区间跨0，不宣称统计显著下降。\n\n'
          '对称参照B的新旧PriorG逐条预测完全相同，均294正确；F4新PriorG相对B新PriorG仅净+1，错误支持+1，PA/MCC差区间均跨0。共同核心有效340条上，F4适配仍比旧F4少对3条；相对B新PriorG正确数持平、MCC略低，说明结论不是由回退制造的。原候选池隔离128条，F4新/旧正确101/102，MCC略升，体现类别取舍而非稳定升级。\n\n'
          '分母对照：对B和F4，更新实际校准类别比例后的prior-only与旧prior-only逐条预测完全相同。本轮F4的5次变动来自加入新G；B虽新G从旧+0.1343变为−0.3238，却没有跨过任何最终分类边界。F4新G=−0.4629，把最终S乘数从约2.7397降到1.6197，NS乘数约0.1982，实际使部分低S分数病例回到NS。\n\n'
          '具体机制限制：改判5条中4条具有完全相同的S/NS/NA=10/85/5，但医生GT为3条S、1条NS。任何只依赖这组三类分数的确定性统一映射，都不能将这4条分别识别正确；这解释了为什么救回一个NS时会同时伤害真实S。此为局部可核对现象，不推断所有错误都不可分。\n\n'
          '研究结论应保留边界：F4的原始判断和固定U2开发收益仍然存在；079否定的是这次简单适配有增益的假设，不是否定F4本身，也不是证明所有可能的后处理无效。当前应保留078的旧配置结果及风险取舍，停止继续追逐这一校准增益，转向论文整理；任何新实验仍需另行交办。')
    c.put(c.OUT/'interpretation.json',dict(short='新F4适配净−3、错误支持−1，无整体升级；停止本次单参数适配，不再搜索，保留F4既有开发信号与原默认，不自动080。',text=text))

if __name__=='__main__':main()
