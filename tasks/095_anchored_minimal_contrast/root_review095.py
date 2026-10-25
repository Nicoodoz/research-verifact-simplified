"""Record actual source reading of the root reviewer's 40 frozen discovery cases."""
from collections import Counter
import common095 as c
NOTES=[
('boundary_scope',[4,6,7,9],'肺部监测有原文，但是否为整个SICU管理重点不能由相关主题直接推出；raw正确而G翻S。'),
('boundary_unknown',[8,11,9,2],'可定位置入支架与病变位置，已读段未建立精确规格和产品身份；不因相同主题填补属性，包外未查。'),
('boundary_relation',[1,2,4,8],'原文分别列心血管治疗与内分泌治疗，不能把药物作用对象并为同一关系；G将原NS改S。'),
('boundary_unknown',[1,2,3,4],'有意识状态片段，但比较词的参照与时点不足；保留原NS及G翻转，不新增临床判标。'),
('boundary_scope',[2,3,4,6],'原文列多个可能诱因，命题仅取其一；是否构成不完整支持属于范围/契约问题，不能由替换词直接裁决。'),
('boundary_time',[10,8,9,1],'有等待专科处理和考虑拔除，但已读段没有直接建立出院前这个时间限制；should不能误当已完成。'),
('boundary_uncertain_cause',[2,4,1,6],'记录多个出血来源可能并排查其中之一；阴性排查不自动证明唯一另一病因，因果归属仍不确定。'),
('boundary_event',[2,6,9,1],'原文有条件式转出安排及术前已稳定记录，术后稳定的概括不能仅凭计划成立。'),
('C48_visible_raw_missed',[7,12,13,8],'原文直接区分大/闭塞性目标阴性与较小目标受限；raw未正确使用此范围，G救回。'),
('boundary_scope',[3,4,6,7],'多日疼痛治疗可见，但全住院范围是概括；不把G救回等同新增取证或严格逐时覆盖。'),
('C48_visible_raw_missed',[8,6,5,10],'同日计划与实际完成记录并存，可定位上午已完成；raw→G救回，仍需区分计划来源和完成来源。'),
('boundary_time_unknown',[7,10,11,4],'已读记录可见后续日期动作，尚未定位原命题所称起始日；G答对不证明这个日期来自输入。'),
('boundary_event_scope',[2,5,4,3],'转入时局部疼痛有记录，但初次入院与后续ICU转入不是同一事件；标签不因此重写。'),
('C48_visible_raw_missed',[1,7,9,10],'问题条目下列出针对可能病因的治疗，原文关联可查；不能要求病历逐字复述泛化治疗句。'),
('missing_date_unknown',[4,6,1,2],'目标日期的所读段主要是检验；另一日期有给液记录。不能用跨日同主题补目标事件；待外部定位。'),
('event_plan_completion',[1,2,3,4],'原文清楚标转入恢复区域为计划，不能将计划视为完成；NA/NS医生契约不由程序重新定义。'),
('event_actor_unknown',[10,3,5],'有相关心律诊断及请求会诊，不直接建立专科曾否认该诊断；需保留说话者/时点。'),
('event_subject_relation',[6,11,5,1],'同一条目标题与正文的反跳对象不同；语义可能依赖标题层次，不能把一处词替换认作医生标注错误。'),
('boundary_context_unknown',[2,5,8,9],'有住院日/术后日与手术背景，没有在已读段定位门诊术前流程和同日入院关系；G额外翻S。'),
('missing_event_unknown',[9,11,10,1],'出院计划、肾功能监测和专科会诊不是同一事件；已读片段未定位原命题的会诊日期。'),
('event_medication_scope',[5,7,8,10],'家中用量增加、暂缓和重新安排均可见；严格方案的全局概括与局部调整存在作用域问题。'),
('event_time_location',[5,1,2,3],'可定位后续用药后低血压，但不能搬到急诊或改变严重程度；同主题与同事件必须分开。'),
('correct_modality_protection',[6,9,12,2],'原命题是可能改善而非已恢复，原文推测/希望与其模态相符；应保护这种S。'),
('correct_time_protection',[8,1,2,4],'术日计划与次日明确完成记录可查，命题术后日不一致；不能仅凭存在同操作判S。'),
('correct_NA_protection',[1,3,6,8],'有用药过量和既往出院材料，不自动建立目标出院装置及便利目的；不拿相关用药事实硬反驳。'),
('correct_value_protection',[10,2,11,3],'可定位输血量及检验变化，命题数值为概括/取整时不宜因细微表述强行反驳；后续结果段见094已核对来源。'),
('correct_polarity_protection',[1,2,6,3],'可定位实际/医嘱通路信息，绝对否定存在问题；同时不把医嘱一律等同完成。'),
('correct_NA_protection',[10,11,1,2],'用药事实与风险推测不同，不能用医学常识填病历未说明的患者级关系。'),
('time_status_unknown',[5,6,9,2],'疗程起始和时长可见，但推算结束日不证明实际停药；不能发明新的停药日期。'),
('missing_route_unknown',[1,2,4,5],'已读段为静脉镇痛及疼痛控制，尚未定位后续改口服；需要包外核对而非捏造替换。'),
('scope_location_ambiguity',[4,5,9,6],'原文有双侧局部发现，命题写单侧不自动与双侧矛盾；这种NS不能简单当位置反事实训练gold。'),
('value_scope_unknown',[12,1,3,4],'给药途径可见，剂量/频次在已读段未建立；不可把相关治疗看作全部属性已有依据。'),
('reason_relation_ambiguity',[8,5,1,6],'治疗调整可定位，但原文所述调整原因与命题因果表述不同；GT为S仍保留，诊断不重标。'),
('scope_time_ambiguity',[4,11,3,2],'原文存在与命题近乎相同的局部/既往描述，GT仍NS；可能时间作用域，不能凭单句判医生错。'),
('correct_event_protection',[8,3,1,10],'原文明确有相应时段的再次事件，应防对比候选把不同时间的另一事件当互斥证据。'),
('correct_NA_time_protection',[1,2,3,4],'局部生命体征与早期转出计划并不建立出院日状态；不能迁移时点。'),
('correct_NA_time_protection',[6,9,1,2],'早期输血及监测不能推出出院时没有追加治疗；缺失不能作负证据。'),
('correct_S_protection',[1,2,4,3],'原文明确记录补液，可用具名液体与给入途径支撑概括；无需逐字相同。'),
('unknown_deidentification',[9,1,3,2],'命题关键对象被去标识占位符遮盖，局部正常影像和异常生命体征并存；不替用户修复原claim。'),
('correct_NA_protection',[1,2,3,4],'已读为检查计划和非同类影像，未定位最终造影残余程度；不能以治疗成功常识补齐。')]
def main():
    rows=[r for r in c.lines(c.PRIVATE/'diagnosis_cases.jsonl') if r['review_owner']=='root'];assert len(rows)==len(NOTES)==40;out=[]
    from diagnosis095 import entries
    for r,(kind,refs,note) in zip(rows,NOTES):
        es=entries(r['reference']);refs=[i for i in refs if i<=len(es)]
        out.append(dict(id=r['id'],group=r['group'],GT=r['GT'],B_raw=r['B_raw'],B_G=r['B_G'],category=kind,interpretation=note,reviewed_reference_ids=refs,source_entry_sha256={str(i):c.h(es[i-1]) for i in refs},read_scope='Four relevance-ranked complete source entries; additional directly cited entries where stated. Not a claim of exhaustive absence.',outside_EHR_verified=False,unknown_retained=('unknown' in kind or 'ambiguity' in kind),reviewer='root_executor',new_medical_gold=False))
    c.putl(c.OUT/'root_source_review.jsonl',out);c.put(c.OUT/'root_source_review_summary.json',dict(utc=c.now(),N=len(out),categories=dict(Counter(r['category'] for r in out)),source_sha256=c.sha(c.PRIVATE/'diagnosis_cases.jsonl'),scope='Source-based descriptive diagnosis; incomplete reference/gold relationship remains unknown.'))
if __name__=='__main__':main()
