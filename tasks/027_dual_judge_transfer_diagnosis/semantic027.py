"""Executor textual observations after complete fixed-packet reading, not new gold."""
import re,collections
import common027 as x
# case, repeated textual issue, bounded observation, literal evidence anchors
NOTES=[
('C01','numeric_time_scope','claim要求medicine floor持续90–120；实际片段含更早/ICU的80–90、85–110及回baseline。两输出已指出范围问题；GT为NA，不能凭这些片段再裁决NS。',['BP b/w 85-110.','BP has returned to baseline.']),
('C02','discharge_time_missing','3月6日改善/仍有腹泻记录与3月7日出院早晨不是同一时间。Gate挡住false-S但退回NS，仍不等于GT NA正确。',['His sx have resolved and he is now eating w/o problems.','Pt had diarrhea x2 in small amount']),
('C03','discharge_time_missing','与C02同类时间覆盖疑问，但医生GT=S；双方低分在固定C48下不能区分这两种GT。未读取其他原始EHR，不归因于医生错误。',['His sx have resolved and he is now eating w/o problems.']),
('C04','exclusive_scope_missing','记录继续home inhaler及D/C Home；inhalers alone把药物/出院范围连在一起。双方理由捕捉限定词，但Q-U2也会S，Gate仍放行。',['will continue home inhaler','Disposition :D/C Home']),
('C05','device_numeric_detail','C48确认LCx置入DES；具体Promus、3.5×15mm未在这些片段核实。两模型都有低支持信号；Gate把原本正确NS改错。',['s/p DES to LCx.','stent placement to a high-grade LCx']),
('C06','procedure_outcome_missing','治疗/置入记录不直接给final angiography residual stenosis结果。Gate挡住W但仍退NS；与C16的完整输入相同、GT却不同。',['stent placement to a high-grade LCx lesion.']),
('C07','test_identity_outcome','reference的CTA无dissection与claim的final angiography事件不完全对应；双方理由均区分事件。GT仍S，不能据此证明GT错或C48必然不足。',['CTA was negative for PE or dissection.','Tolerated procedure well.']),
('C08','plan_relative_time','reference确有cath计划和echo，但further的相对时间未在claim指定。双方理由把它理解为之后的追加检查；具体GT差异机制unknown。',['cath this a.m.','Test: Portable TTE (Complete)']),
('C09','negative_assertion_scope','CT无急性影像异常与ED无感染迹象不是同一命题。双方低支持；不采纳Qwen关于感染鉴别的外部医学推断为gold。',['No acute intracranial hemorrhage, edema or mass.']),
('C10','plan_vs_completion_destination','冻结片段有probable inpatient psych/待评估；实际完成转院及具名目的地没有在这些片段建立。双方低分未阻止Gate放行。',['Probable inpatient psych admission once medically stable.','Psychiatry will evaluate for the possible need for an inpatient stay.']),
('C11','causal_relation_modality','bicarb与低K共同出现；could be related是弱可能关系，模型理由按显式因果要求处理。Gate挡W但未修正为GT NA；不独立判断药理因果。',['K: 4.6->3->2.7','bicarb drip']),
('C12','serial_stability_time','记录2.7后补钾到3.3及继续管理；now stable after multiple checks是更长时间的综合判断。两模型低分，Gate仍放行。',['Hypokalemia: got 40mEq of K x2 and 40mEq IV for level of 2.7. 3.3 on']),
('C13','condition_action_identity','片段查finger fracture/未见acute fracture；claim是trigger finger的手术必要性，病名和决策范围不同。挡W不等于最后NS正确。',['There is no evidence of acute fracture.','Hand to see patient, do not think it is fractured.']),
('C14','medication_route','C48药名列表有Heparin，drip属性未明确；Qwen把药名当作drip支持、S100，D理由明确缺route。不是两个Judge共同高S，而是Qwen单边过强支持。',['15. Heparin','Infusions: Amiodarone']),
('C15','discharge_indication_missing','Afib控制及IVC影像不直接给Coumadin出院指征。原D U0=NA且正确，Gate拒绝保留正确NA；不可把Qwen理由的临床常识当验证事实。',['Afib rate controlled on PO Metoprolol and Diltiazem','Intraoperative image of IVC filter deployment.']),
('C16','procedure_outcome_missing','C48有术中部署图像，未给明确无并发症结果句；医生GT=S。与C06同一D/Q输入向量，因此无score-only确定性Gate可分别取正确动作。',['Single spot fluoroscopic image from IVC filter deployment.']),
('C17','focus_vs_component','Q2h neuro checks确有记录；两理由把focus加严为sole/primary，与多系统管理对照。GT=NS保持；这个限定词解释是可见输出行为，不是独立医学判定。',['Q2h neuron checks.','Afib rate controlled on dilt drip']),
('C18','focus_vs_component','呼吸监护和治疗确有记录；同样focus被解释为sole/primary。与C17/C19属于同患者同句型相关错误，不能当三个独立患者机制复现。',['Closely follow resp. status','PULM: Aggressive pulm toilet.']),
('C19','focus_vs_component','肾功能监测确有记录；两理由仍依据多系统管理否决focus。Gate将正确NS改成S，语义裁决本身仍不由本任务重标。',['RENAL: boderline urine output, monitor Cr.']),
('C20','numeric_remainder_scope','早期Hct低值与后期29–32附近值共存；remainder的起点未在原子claim给出。双方按全住院范围反驳而GT=S，是时间范围/关系压缩疑问。',['Hct 29.3 29.2 27.9 30.1 30.4 29.7 29.5','Hematocrit: 24.5']),
('C21','diagnostic_relation_modality','reference同现small temporal SAH及hyperdensity可为hemorrhage/calcification；instead被模型读作排除/替换关系。GT=S保持，是否应接受这种转述unknown。',['Punctate hyperdense focus in the left temporal lobe which may represent hemmorhage or calcification.']),
('C22','deidentification_time_ambiguity','[**5-27**]与通气设置和8月日期同现；两输出都质疑日期读取。不得把模型推测的原始设置当已还原事实。Gate保留GT NS。',['did well on [**5-27**] but not following commands','tolerating PSV 5/5 well.']),
('C23','syndrome_vs_observation','reference有respiratory failure/aspiration与低氧数据，但这些片段未明确ARDS名称。双方低分；不自行以生理标准新增ARDS医学标签。',['Billing Diagnosis: (Respiratory distress: Failure)','PaO2 / FiO2: 148']),
('C24','summary_trajectory','可见胸痛缓解、撤NTG、术后耐受；D要求持续全住院明确语句，Q接受轨迹概括。作为GT R正确保留对照，说明Q信号确有用。',['Ntg weaned off.','Tolerated procedure well.']),
('C25','inconsistent_numbers_intent','记录Tylenol数量30/40/20并存，双方低分却GT=S，Gate正确保留。说明数字冲突理由并不总对应应拒绝；不重判服药意图。',['50 tablets of aspirin and 40 tablets of tylenol.','50 tablets of aspirin and 20 tablets of tylenol.']),
('C26','service_name_inference','C48有BLUNT TRAUMA/TSICU；D要求明确服务名称，Q接受其作为Trauma Service支持。仅记录判定范围差异，不借模型扩写机构缩写为新的gold。',['was sent back to TSICU','Admitting Diagnosis: BLUNT TRAUMA']),
('C27','single_vessel_scope','单LCx病变/单DES确在片段，Q接受one-vessel归纳、D要求排除其他血管。R对照不能证明此归纳普遍医学有效。',['L mid-circ 90% lesion (left dominant system), single DES placed']),
('C28','prior_vs_current_treatment','记录No recent abx与本次ED levofloxacin共存。Q接受既往用药句，D把本次给药作冲突；时间scope可解释两者差异，但不证明内部机制。',['No recent abx use makes C. diff less likely.','Was treated with levofloxacin']),
('C29','possible_cause_history','既往头痛may have been migraines与本次头痛并存；Q接受possible cause、D要求本次明确因果。R对照与C14具有完全相同D/Q特征，临床关系不同。',['She has a inconsistent h/o prior HA which may have been migraines.']),
('C30','medication_purpose_scope','药名Heparin存在；双方把manage coagulation进一步要求明确治疗指征，但GT=S、Gate保留。与C14的具体drip属性问题不同，score不表达这个差别。',['15. Heparin','DVT: Boots']),
('C31','stability_vs_variation','HR数值变化和VSS并存；双方把stable读作更少数值变化，GT=S、Gate保留。低Q支持不等于应拦截，是误伤风险对照。',['Pt BP and HR runs low with sleeping and rest, team aware.','Heart Rate: 64 bpm'])]

def run():
    x.offline();root=x.OUT/'case_material_001';out=x.OUT/'semantic_001';records=[]
    for case,tag,note,quotes in NOTES:
        r=x.read(root/(case+'.json'));anchors=[]
        for quote in quotes:
            pattern=r'\s+'.join(re.escape(s) for s in quote.split());m=re.search(pattern,r['reference']);x.c.require(m is not None,case+' quote not found: '+quote)
            header=list(re.finditer(r'(?m)^\d+\. Date:.*?\| Text:',r['reference'][:m.start()]))
            anchors.append(dict(start=m.start(),end=m.end(),quote=r['reference'][m.start():m.end()],entry_header=header[-1].group() if header else None))
        records.append(dict(case_id=case,proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=r['features']['GT'],RHW=r['kind'],keep=r['keep'],role=r['role'],textual_issue=tag,observation=note,mechanism_status='textual_hypothesis_not_causal_proof',clinical_adjudication='unknown_not_relabelled',full_packet_read=True,reference_read_via='reading_view_001/case_block_mapping.json + complete case reference',D_S=r['D_scores']['Supported'],Q_S=r['Q_scores']['Supported'],Q_U2_supported=bool(x.c.decode(x.c.logs(r['Q_scores']),2)==0),gate_probability=r['gate_probability'],anchors=anchors,source_sha256=x.sha(root/(case+'.json'))))
    x.c.require(len(records)==31 and {r['case_id'] for r in records}=={r['case_id'] for r in x.read(root/'index.json')},'Reading coverage differs')
    out.mkdir(exist_ok=False);x.put(out/'case_ledger.json',records)
    md=['# 027逐例文本诊断（非新增医学gold）','','固定31例：17错误、6正确拒绝风险、8正确保留R。全部原claim/reference及两模型完整输出已读；编号对应case_material_001。引文偏移是该case reference的Python字符半开区间。','']
    for r in records:
        md.extend([f"## {r['case_id']} · {r['role']} · {r['RHW']} · keep={r['keep']}",'',r['observation'],'',f"D-S={r['D_S']}，Q-S={r['Q_S']}，Q-U2支持={r['Q_U2_supported']}，Gate概率={r['gate_probability']:.6f}。",'',*[f"- reference[{a['start']}:{a['end']}]：`{' '.join(a['quote'].split())}`" for a in r['anchors']],'',f"完整材料：../case_material_001/{r['case_id']}.md。临床归因unknown，不修改GT。",''])
    (out/'case_notes.md').write_text('\n'.join(md),encoding='utf-8')
    x.put(out/'manifest.json',dict(inputs={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in [x.TASK/'semantic027.py',root/'manifest.json',x.OUT/'reading_view_001/manifest.json']},outputs={p.name:x.sha(p) for p in out.iterdir() if p.is_file()}))
    print('31 case observations and',sum(len(r['anchors']) for r in records),'verified anchors saved')
if __name__=='__main__':run()
