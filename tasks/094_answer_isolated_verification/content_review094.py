"""GT/final-verdict blind description of all extraction differences, not new gold."""
from collections import Counter
import common094 as c
CATEGORIES={
 'dd6a7f62-eba8-03af-b8d9-0eb43b35df8c':('same_fact_wording','同一数值变化和引用，主要措辞差异'),
 '9e73b952-c841-0496-9c38-6acf3e5c6664':('same_fact_wording','缩写展开及时间格式，所引事实相同'),
 '3a5a7f4c-d956-f07f-7d23-bcb3659e3427':('same_fact_wording','同一状态、引用，12/24小时写法差异'),
 '44fdab61-34d4-71e8-9908-3bc7429192ae':('same_fact_wording','同一事件，状态和时间描述详略不同'),
 '35894a8a-c8d8-3e47-5358-6f3565a817f7':('same_fact_wording','同一地点，缩写展开和状态表述不同'),
 '575b384f-3a90-c057-8095-c2cf46770443':('same_fact_citation_count','同一属性，Q多给一处重复支持引用'),
 '58199cb8-0a7b-a74e-4922-1c6fec3ba2b1':('same_fact_citation_count','同一检查事件，Q少给一处引用'),
 '57d58ad8-24c3-c0e7-c488-6ea193dee45c':('coverage_changed','V给出直接事件引用，Q报告不足；隔离可能损失定位线索'),
 '5dcc5638-024a-f443-f920-ce04707baf3e':('coverage_changed','V不足，Q提供疾病/照护方向；引文定位不证明其主要目标概括完整'),
 '197fbcad-e09e-f5fa-504e-19df52c6435a':('coverage_changed','V不足，Q概括某时点照护位置；引文提及术后日和转出安排，须区别安排与完成，不能把Q答案当gold'),
 '1da2eed5-19d1-76f9-ae93-679c847f077d':('invalid_record_difference','Q引用编号不匹配导致不可用；非合法评分边界机制'),
 '3415aeb0-9dea-755a-5880-e40755e8ad61':('invalid_record_difference','Q含非连续拼接引用导致不可用；不强行修复答案'),
 '949cae52-2eaf-26ed-6782-36be766b7a13':('invalid_record_difference','V第二引用未能匹配导致整记录不可用，Q引用合法；工程可用性差异需单列')}
def main():
    rs={(r['id'],r['arm']):r for r in c.lines(c.PRIVATE/'extracted_aligned.jsonl')};out=[]
    for pid in sorted({k[0] for k in rs}):
        same=rs[pid,'V']['record']==rs[pid,'Q']['record']
        if same:category,note='identical','校验后记录逐字段相同，共享最终请求'
        else:category,note=CATEGORIES[pid]
        out.append(dict(id=pid,category=category,interpretation=note))
    c.put(c.OUT/'content_review.json',dict(utc=c.now(),GT_consulted=False,final_predictions_consulted=False,new_medical_gold=False,independent_audit=False,counts=dict(Counter(r['category'] for r in out)),rows=out,raw_source_sha256=c.sha(c.PRIVATE/'extracted_aligned.jsonl')))
    print(dict(Counter(r['category'] for r in out)))
if __name__=='__main__':main()
