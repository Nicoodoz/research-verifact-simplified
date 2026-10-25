"""Serialize independently read source observations; no automated medical labeling."""
import json,hashlib,re
from pathlib import Path
R=Path(__file__).resolve().parents[2]
notes=[
([4,9,11],['boundary_tradeoff','relation_scope','unknown'],'病历考虑多种心肌酶升高原因，并记载短暂低血压及停抗凝；这不直接证明命题排除某种血栓机制。raw正确而G转S，不能据临床推测补上因果排除。'),
([5,7,10,12],['boundary_tradeoff','attribute_scope','unknown'],'置管及尿液引流有直接记录；命题另加大量这一数量限定，所读段未给出对应定量。raw到G使部分事实支持扩为全命题支持。'),
([1,2,3,8],['boundary_tradeoff','relation_scope','unknown'],'多日用药清单能确认药物暴露，所读来源未将其与命题所称感染适应证连接。不能从用药存在推断特定治疗理由。'),
([1,3,5,6],['boundary_tradeoff','uncertainty_scope'],'影像给出不张与感染的鉴别、感染未完全排除；命题概括为提示特定疾病。确定性强弱是实际差异，G将raw的NS翻为S；不在这里改医生标签。'),
([5,6,7,9,11],['boundary_tradeoff','relation_scope','in_pack_discriminating_information'],'药物方案确在记录内，但后续明确归于另一器官综合征；病人同时低血压不能自动证明所称适应证关系。'),
([1,2,3,7],['boundary_tradeoff','time_scope','unknown'],'相关心电文字是一次与既往比较，无显著变化不能自动覆盖后续全部检查。其余所读来源不补足该时间量词。'),
([1,2,4,10],['boundary_tradeoff','attribute_scope'],'神经检查与其他监护治疗共同出现；存在某项护理并不直接证明它是全部重症管理的重点。'),
([3,7,8,9],['boundary_tradeoff','relation_scope'],'转普通病房计划/处置记录可见，康复目的未在所读来源对应。转移目的与转移事件需分别核验。'),
([9,11,12],['boundary_tradeoff','status_scope','unknown'],'多处写转病房处置或当晚计划，所读段未直接给出转移完成回执。G救回与GT一致，但不是增加证据；不能硬性把计划一律判错。'),
([2,4,5,8],['boundary_tradeoff','time_scope'],'多时点酸碱问题和治疗可见，命题的全住院期间范围更宽。该例G救回显示过严全程证明要求也可能伤害真S。'),
([2,10,1,3],['boundary_tradeoff','broad_summary','unknown'],'来源覆盖手术、呼吸支持与并发症预防处置；命题是宽泛概括，不对应一个明确单点取值。无法仅凭摘录唯一裁决全程范围。'),
([3,4],['boundary_tradeoff','in_pack_discriminating_information'],'原文直接记载缺损和分流方向，raw NS被G纠正；本例关键关系在包内，不能简单归为缺证据。检查类型身份需与同份Echo元数据一起读。'),
([1,5,3,8],['boundary_tradeoff','unknown'],'所读片段主要为术前手术会诊、肌力体检与术后呼吸体检，尚未直接定位命题的治疗师会诊。G正确不等于已补得该证据。'),
([2,3,5,7],['boundary_tradeoff','time_scope','route_scope','unknown'],'所读术后镇痛为静脉自控及硬膜外，命题限定首日口服。GT为S仍保持原样，未穷尽原EHR，不能据当前摘录改标。'),
([5,6,9,11],['in_pack_discriminating_information','relation_scope'],'多份来源明确把该药用于相反的酸碱状态。关键替代取值有包内依据；B判NA而GT为NS，属于关系/状态区别未体现在最终标签，不是单纯没提药物。'),
([3,7,12,4],['in_pack_discriminating_information','uncertainty_scope'],'内镜后倾向某出血来源的叙述多次出现；命题用揭示语气更确定。GT为S而B为NS，说明确定性词差异不能直接充当普适否决规则。'),
([11,1,2,3],['entity_scope','unknown'],'有外院就诊和后续治疗背景，命题含去标识姓名；当前摘录不足以完成姓名与转院事件绑定，不能猜测匿名标识等价。'),
([1,2,3,4],['relation_scope','unknown'],'已读来源涉及胆道感染和多器官表现，未直接定位命题指定生化指标的病因解释。未查全EHR，不能声称包外已找到反证。'),
([9,2,3,5],['in_pack_discriminating_information','time_scope'],'早期夜间仍有一次症状，较晚医生记录症状消退并进食正常。需要按时序整合；只抓早期残留事件会伤害最终恢复的S。'),
([8,1,2,3],['unknown','lab_identity'],'已读段主要是低血压与容量状态，不能直接从疾病背景推出命题的电解质诊断。实验室表格部分截断且缺指标对应，保留unknown。'),
([8,6,10,1],['time_scope','numeric_scope','unknown'],'当前摘录有多日期的其他血细胞比容值，部分表格在指标名处截断；未定位命题精确日期与最低值组合。不把任意邻近数值当该事件反证。'),
([6,9,10,1],['in_pack_discriminating_information','status_scope','time_scope'],'早期因风险开始药物，后续因检测不在毒性范围而停药。停止/开始必须对应时点；后续停药依据在C48已可见但B仍NS。'),
([8,1,2,3],['entity_scope','unknown'],'命题药物主体缺失且带去标识片段；相关C48的起搏设置、抗凝处置不能绑定该剂量。正确NA为保护病例，勿用无关数值造近邻。'),
([11,7,9,2],['correct_protection','in_pack_discriminating_information'],'即使导管相关并发症存在，团队明确决定当前装置仍可使用。并发症本身不构成禁止使用的证据；应保护这个真S。'),
([1,4,5,2],['correct_protection','uncertainty_scope'],'记录明确列休克病因未明及多个备选；直接命名某单一病因会过度确定。保留原NS，不将备选病因当已证实。'),
([4,1,2,3],['correct_protection','unknown','drug_identity'],'所读心律处理明确另一药物，未定位命题药物。另一药物存在不证明两者排他，故不能仅据此把NA改NS。'),
([11,1,2,3],['correct_protection','in_pack_discriminating_information'],'出院后与医生门诊随访安排有直接记录。问题不在主题词匹配，而是保留计划作为适当支持的时间语义。'),
([3,8,10,4],['correct_protection','status_scope','time_scope'],'多个家用药继续，但某药曾暂缓，稍后又恢复。全称全部不能由部分继续推出；时序与全称范围共同重要。'),
([2,9,1,3],['status_scope','unknown'],'多日写转病房计划，未在已读段看到完成。不能把计划未见完成直接当反证；GT为NA而B为NS体现缺证与矛盾的边界。'),
([10,5,3,11],['status_scope','time_scope','unknown'],'当时仍计划满足条件后做检查；命题是最终决定不做，可能指较晚节点。未读完整后续，现计划不必然反驳最终决定，保留NA原GT。'),
([6,11,12,13],['entity_scope','status_scope','unknown'],'家属代理身份和家属沟通/会议安排可见，但命题具体医生参与的已完成会议未唯一定位；去标识身份和计划时点是限制。'),
([1,2,3,4],['in_pack_discriminating_information','procedure_identity','unknown'],'包内记录球囊扩张及溶栓尝试，命题是支架。操作名称可区分，但所读摘录不覆盖全部后续，不能将没看见支架等同从未放置。'),
([7,10,11,1],['relation_scope','unknown'],'康复计划针对呼吸、活动和力量；肥胖背景同时存在，未建立康复专门治疗肥胖的关系。NA与NS差异不能靠一般医学推理补足。'),
([13,2,6,7],['status_scope','unknown'],'来源能支持术后稳定恢复与出监护的背景，但所读段尚未直接绑定已在普通病房继续恢复。原GT为S，限制归于证据定位而不改GT。'),
([1,2,10,4],['correct_protection','in_pack_discriminating_information','numeric_scope'],'原文直接给出基线区间，当前升高值另记。命题区间不同；这是有明确同一指标/基线语境的最小数值差异。'),
([5,8,9,10],['correct_protection','in_pack_discriminating_information','numeric_scope'],'正式影像给精确比例，进展记录给包含它的范围。近邻取不同但重叠范围时，两个说法可能都得到支持，不能强制二选一。'),
([1,2,3,4],['correct_protection','status_scope','unknown'],'所读来源为术后持续通气、撤机准备与模式调整，不等于已拔管后再次插管。是否有后续事件尚未穷尽，只保留原NS作保护。'),
([8,6,11,3],['correct_protection','status_scope','unknown'],'可见贫血监测和达到阈值才输血的计划，未在已读段定位命题的已完成定量输血。计划阈值不是实际给血回执。'),
([7,6,8,1],['correct_protection','in_pack_discriminating_information','event_alignment'],'起床时低血压及停药后缓解在同一护理事件中直接对应，可保护真S，不能因另有正常血压就否定该事件。'),
([9,6,10,1],['correct_protection','in_pack_discriminating_information','status_scope'],'先给予减量并继续观察，后续考虑病情恶化才停；减量、条件性暂缓与已停药不是同一状态。')
]
def main():
    p=R/'.local_models/095/diagnosis_cases.jsonl'
    cases=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if json.loads(x).get('review_owner')=='independent_source_reviewer']
    assert len(cases)==len(notes)==40
    out=[]
    for idx,(x,(ids,tags,note)) in enumerate(zip(cases,notes)):
        starts=list(re.finditer(r'(?m)^\d+\. Date:',x['reference']))
        entries={int(m.group().split('.')[0]):x['reference'][m.start():starts[k+1].start() if k+1<len(starts) else len(x['reference'])] for k,m in enumerate(starts)}
        refs=[]
        for no in ids:
            e=entries[no];span=re.search(r'Raw characters: \[(\d+),(\d+)\)',e);body=e.split(' | Text: ',1)[1][:int(span.group(2))-int(span.group(1))]
            refs.append(dict(reference_id=no,note_id=re.search(r'Note ID: ([^,]+)',e).group(1),source_entry_sha256=hashlib.sha256(e.encode()).hexdigest(),raw_text_sha256=hashlib.sha256(body.encode()).hexdigest()))
        out.append(dict(id=x['id'],sid=x['sid'],review_index=idx,reviewer='independent_source_reviewer',GT_unchanged=x['GT'],B_raw=x['B_raw'],B_G=x['B_G'],group=x['group'],tags=tags,observation_zh=note,citations=refs,scope='相关C48来源原文阅读；不是完整EHR穷尽核验',outside_C48_located=False,medical_gold=False,reference_sha256=hashlib.sha256(x['reference'].encode()).hexdigest()))
    dest=Path(__file__).parent/'source_review.jsonl'
    with dest.open('w',encoding='utf-8',newline='\n') as f:
        for row in out:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
    print('wrote',len(out),'independently read observations')
if __name__=='__main__':main()
