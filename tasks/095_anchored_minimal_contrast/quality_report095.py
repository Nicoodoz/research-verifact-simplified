from collections import Counter
import common095 as c

def main():
    root=c.lines(c.OUT/'root_construction_quality_review.jsonl');ind=c.lines(c.ROOT/'reviews/095_anchored_minimal_contrast/construction_quality_review.jsonl');rows=[]
    for r in root:rows.append(dict(id=r['id'],panel=r['panel'],reviewer=r['reviewer'],status=r['status'],explanation_zh=r['explanation_zh'],source_file='root_construction_quality_review.jsonl'))
    for r in ind:rows.append(dict(id=r['id'],panel=r['panel'],reviewer=r['reviewer'],status='plausible_single_property' if r['judgment']=='good' else r['judgment'],explanation_zh=r['observation_zh'],source_file='../../reviews/095_anchored_minimal_contrast/construction_quality_review.jsonl'))
    assert len(rows)==len({r['id'] for r in rows})==24
    c.putl(c.OUT/'construction_quality_24.jsonl',rows);c.put(c.OUT/'construction_quality_summary.json',dict(N=24,counts=dict(Counter(r['status'] for r in rows)),panels={p:dict(Counter(r['status'] for r in rows if r['panel']==p)) for p in ['natural','mechanism']},reviewers=dict(Counter(r['reviewer'] for r in rows)),sample_rule='fixed hash12 natural+12 mechanism among automatic eligible, exclude16 pilot; no GT or correctness selection',limitations='stratified descriptive source reading, not physician gold or estimated failure prevalence over all95; unknown distinct from violation; no deployment filtering',root_hash_scheme='SHA256(header + body) in root_construction_quality_review; delimiter excluded deterministically; independent full-source and raw-text hashes per own generator'))
    text='''# 095 构造源文案例：为何数量通过仍不进入分类

300次构造和117次核对均获得唯一HTTP200；自然67、富集28被自动检查判为拟触发，共95条/65患者，数量gate通过。最终Judge尚未运行，所以本页**没有分类救回/伤害案例可报告**，不能编造C−B或C−E效果。

预检16例的3个自动通过中，两个确定违反保留时点或并列作用域，另一个同事件unknown。修复仅针对空白绑定，恢复5个程序误拒，不改变生成内容，也未证明恢复者语义正确。原4个成功checker没有重发。

随后在95个自动通过中按固定哈希分别取自然12、富集12，并排除预检16例；两位执行者各读12、全程不看GT/分类成绩。24例为可读单属性8、明确违反8、unknown8，分层组成不同于95总体，不能直接当总体失败率，也不是医生新gold。可读只指来源与编辑关系能被检查，不要求替代命题为真或两假设互斥。

|类别|病例ID|具体可观察问题|为什么影响本轮机制|
|---|---|---|---|
|时点迁移，预检|6b135b91-e733-0b6e-d415-1f90c5f85d9d|治疗后改善被放入仍保留最初时点的句子|取值出现不等于原时点的同一属性有依据|
|并列对象，预检|4bce1c25-3f10-c56a-b38b-4d851402a48d|两药共同改成已恢复，原文一药已执行、另一药仅计划且通路条件变化|单个字符串跨度隐藏多对象状态变化|
|仅同义替换|5058b3ea-dd24-6ee7-fa32-fba13dbcc5e0|按需与其缩写互换，被核对器判为实质不同|增加文字但没有真正比较不同事实条件|
|多属性编辑|e0ace8de-39cd-a3d2-7ef3-ef7bf24cd25b|一般补液同时加总量与液体类型|不能把一处文本span等同一个临床属性|
|关系绑定错误|4b30257f-dd23-eb36-dd40-950039006edd|另一药物对应的敏感状态被移给原命题保留的药物|同一患者、菌种或检测主题不足以保证具体关系对应|
|无法唯一定位事件|37edddb4-750c-7dbd-fb76-286df03fccb2|材料提及多次操作和不同专科，替代身份有出处但事件不唯一|保留unknown，不把同部位当同一次事件|
|可读的数值对照|31c20839-46c7-f573-50e7-aec204f72d39|同一问题条目直接给替代数值与基线范围|说明并非所有构造都无效；仍不认证全病程峰值或医生标签|
|可读的时间粒度对照|acba0fcb-29f8-3ced-49fc-c989eb52b720|来源绑定同次操作、给药与过程，近邻只放宽时间粒度|两命题可能同时成立，不能强制反事实为假或二选一|

完整来源编号、哈希与抽象说明见[24例记录](construction_quality_24.jsonl)、[root原记录](root_construction_quality_review.jsonl)、[独立来源记录](../../reviews/095_anchored_minimal_contrast/construction_quality_review.jsonl)。临床原文保留在私有目录，不推送。

本轮停止的是未经可靠同事件/限定核对的构造版本，而非“对比核验分类效果为负”。不将人工读出的好例子组成收费分类队列，否则会把执行者选择器冒充可部署规则。重启至少需要一个统一可执行的时间、对象和并列作用域约束，在独立于方法构建的固定盲样本中先证实能排除这些误放行，保留足够真实操作量，再做B/E/C。不能仅增加一句核查提示或换名后继承本轮可信度，本轮不自动执行。
'''
    with (c.OUT/'candidate_cases.md').open('w',encoding='utf-8',newline='\n') as f:f.write(text)
    print(Counter(r['status'] for r in rows))
if __name__=='__main__':main()
