"""Record GT-blind reading, not a deployed gate or physician relabeling."""
from collections import Counter
import common095 as c
import method095 as m
NOTES=[
('definite_violation','原词与替换词是按需及其缩写，事实条件没有改变；自动核对把同义写法认作实质差异。'),
('plausible_single_property','同一操作的原文给出返回病区后很快发生这一时间关系，近邻改动时间具体性；不保证两说法互斥，也不认证完整命题。'),
('definite_violation','在一般补液上同时补入总量和具体液体类型，连续跨度虽然只有一处，却改变两个独立属性。'),
('definite_violation','从既往病史否定换成当前急性检验变化，同时迁移时间范围、对象层次与极性，不是单一属性近邻。'),
('definite_violation','引用中的敏感状态对应其他药物，却保留原命题的目标药物；同一患者和检测主题不等于同一药物—敏感性关系。'),
('plausible_single_property','源文明确给出当日下午的清醒程度，近邻增加一个时间限定；仍只是可核对假设，不据此重标原命题。'),
('unknown','相关原文提到两次关节操作及不同专科，取值有出处但不能唯一确认它与原命题是同一次操作；不把同部位视为同事件。'),
('definite_violation','把住院过程中的暂时禁食状态直接放进出院状态命题，所引出处没有建立出院时点绑定；这不宣称真实出院状态必定相反。'),
('plausible_single_property','同一肾功能问题条目直接给出替代数值及基线范围，表面仅改数值；不据局部值认证完整病程最大值或医生标签。'),
('unknown','饮食类型有直接出处，但原命题保留的持续时间与尝试升级过程未被该段绑定；现有阅读不能认证同一过程。'),
('unknown','原命题对并列部位的范围修饰存在歧义，替换可能只是明确原意而非新事实条件；不能自动认证实质差异。'),
('plausible_single_property','来源同时绑定给药量与操作过程，将精确起始时点放宽到操作期间，保留其余事实；单一时间粒度变化可读但两说法不互斥。')]

def main():
    sample=[r for r in c.lines(c.OUT/'construction_quality_sample.jsonl') if r['reviewer']=='root'];vv={r['id']:r for r in c.lines(c.PRIVATE/'checked.jsonl')};inputs={r['id']:r for r in c.lines(c.PRIVATE/'screen_inputs.jsonl')};out=[]
    assert len(sample)==len(NOTES)==12
    for r,(status,note) in zip(sample,NOTES):
        v=vv[r['id']];refs=m.entries(inputs[r['id']]['reference']);ids=[a['reference_id'] for a in v['anchors']]
        if r['id']=='37edddb4-750c-7dbd-fb76-286df03fccb2':ids=sorted(set(ids+[7,10,11]))
        out.append(dict(id=r['id'],panel=r['panel'],reviewer='root_executor',status=status,explanation_zh=note,reference_ids=ids,source_entry_sha256={str(i):c.h(refs[i]['header']+refs[i]['text']) for i in ids},read_scope='Constructor anchors and complete cited C48 entries; targeted additional entries for recurrent procedure ambiguity. No GT or predictions read.',new_medical_gold=False,used_for_deployment=False))
    c.putl(c.OUT/'root_construction_quality_review.jsonl',out);print(dict(Counter(r['status'] for r in out)))
if __name__=='__main__':main()
