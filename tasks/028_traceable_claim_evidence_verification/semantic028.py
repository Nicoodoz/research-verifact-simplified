"""Executor observations with verifiable original spans; never changes predictions/GT."""
import re
import common028 as c
NOTES=[
('K01','remaining_shared_rejection','新表示仍将最终造影无残余狭窄整体记unaddressed；与K02没有形成相反放行动作。原GT为NA，但候选流程退U0=NS，不能把拒绝S等同三分类已正确。',['stent placement to a high-grade LCx lesion.']),
('K02','remaining_shared_rejection','拆解仅一行，把发生程序和无并发症并在一起；C48有部署图像，未明确给出无并发症句。双方仍拒绝GT S；不据此重判GT。',['Single spot fluoroscopic image from IVC filter deployment.']),
('K03','attribute_boundary','新核查引用实际Heparin药名，区分drip属性未涉及，阻止SD原H。普通repeat也作相同拒绝，所以该例不是新结构独有收益。',['15. Heparin','Heparin Sodium']),
('K04','modality_scope','引用may have been migraines并接受possible cause，保住与K03分数完全相同的R；普通repeat拒绝。可见新输出区分了两种主张关系，但历史病史到当前病因的医学充分性仍unknown。',['She has a inconsistent h/o prior HA which may have been migraines.']),
('K05','citation_index_failure','模型关系标签为supported且给出多条进步证据，但首引文错标5而实际在4。按预登记所有引用需可定位的规则回退，造成真R误伤；其余有效引文不能事后用来改放行规则。',['Response: Propofol off, took pt several hours to be responsive','Much more awake, indicating pain, following some commands']),
('K06','supported_relation_not_established','两行形式上拆开属性和POD日期，但从dry dressing推到dry incision、又将10-02直接指定POD2；所引句不自证这些关系。引用存在仍可错误支持GT NA，不重新裁定术后日序或GT。',['Surgical dressing at right hip CDI.','no sign of bleeding through wrap noted.']),
('K07','action_vs_later_stop','新核查引用also started on vanco/zosyn保留曾接受抗生素；repeat一边引用启动又以之后停止否决。原文已在同C48，不是新增证据召回。',['also started on vanco/zosyn.','STopping antibiotics as above.']),
('K08','qualifier_strength_risk','新requirement把focus写作primary focus并因无显式focus句记uncertain，阻止GT NS；但不能凭标签改对证明主张强度得到保真，仍有013式加严的风险。',['PULM: Aggressive pulm toilet. Tolerating IS','Closely follow resp. status']),
('K09','specific_date_gap','新核查保留8-20日期要求，C48有8-5至8-8及8-24之后记录但缺目标日条目，故拒绝GT S；普通repeat按持续性推断放行。不是新医学gold，未补目标日证据到模型。',['CXR w/ persisent RLL collapse.','alterating TM with CPAP 10/5 to keep RLL open']),
('K10','condition_and_action_conflation','引用确有no acute fracture/手外科不认为骨折，但它并不等于trigger finger不需要手术。新fact关系反而把缺手术记录作为支持，产生新W；表格可追溯不等于语义关系正确。',['There is no evidence of acute fracture.','Hand to see patient, do not think it is fractured.']),
('K11','summary_support_scope','将支持措施和throughout分成两项，引用不同日期的呼吸/营养护理，放行GT S；repeat要求出现other supportive measures这一类别词而拒绝。观察支持范围差异，不认证全住院每时刻的事实。',['Pulmonary: Trach, CPAP at night, trach mask trials during the day','requiring placement of Peg/trach for feeding and pulmonary toileting'])]
def locate(quote,text):
    spans=c.matches(quote,text);c.require(bool(spans),'Anchor absent: '+quote);a,b=spans[0];return dict(start=a,end=b,quote=text[a:b])
def run():
    out=c.OUT/'semantic_001';records=[];diag=c.OUT/'diagnosis_001'
    for case,tag,note,quotes in NOTES:
        r=c.read(diag/(case+'.json'));records.append(dict(case_id=case,proposition_id=r['row']['proposition_id'],GT=r['row']['GT'],selection=r['selection'],observation=note,textual_pattern=tag,medical_adjudication='unknown_not_relabelled',claim_and_full_C48_and_both_outputs_read=True,anchors=[locate(q,r['reference']) for q in quotes],source_sha256=c.sha(diag/(case+'.json'))))
    extras=[]
    for case,queries,note in [
      ('K01',['residual stenosis'],'历史发布reference中未定位到该短语；这不是完整EHR遍历，也不说明GT错误。'),
      ('K02',['complication','Single spot fluoroscopic image'],'发布reference有更多部署影像文字，未定位到complication词；仍不能判定有无并发症。'),
      ('K03',['SQ UF Heparin','Heparin Sodium (Prophylaxis)'],'发布reference可定位SQ/Prophylaxis，比C48片段药名更具体；只作来源差异诊断，不能断言全部病历均无drip。'),
      ('K04',['may have been migraines'],'相关may have been migraines在C48也已存在，非新增证据；支持关系解释而非是否检索到词组仍是观察重点。')]:
        r=c.read(diag/(case+'.json'));p=diag/('extra_'+r['row']['proposition_id']+'.json');extra=c.read(p);hits=[]
        for query in queries:
            for start,end in c.matches(query,extra['reference']):hits.append(dict(query=query,start=start,end=end,quote=extra['reference'][start:end]))
        extras.append(dict(case_id=case,source=p.relative_to(c.ROOT).as_posix(),source_sha256=c.sha(p),queries=queries,hits=hits,observation=note,not_full_EHR=True,not_sent_to_API=True,GT_unchanged=True))
    out.mkdir(exist_ok=False);c.put(out/'case_ledger.json',records);c.put(out/'evidence_source_checks.json',extras)
    md=['# 028 执行者文本诊断','','固定11例，观察非新增医学gold；全部C48/两模型输出已读，四个旧case的C48与027冻结材料一致。','']
    for r in records:
        md.extend([f"## {r['case_id']} · {r['textual_pattern']}",'',r['observation'],'',*[f"- C48[{a['start']}:{a['end']}]：`{' '.join(a['quote'].split())}`" for a in r['anchors']],''])
    md.extend(['## 额外来源诊断','','仅检查四条历史发布reference的相关句段，不是完整患者EHR审计。额外材料未送API。',''])
    md.extend([r['case_id']+'：'+r['observation'] for r in extras]);(out/'case_notes.md').write_text('\n'.join(md),encoding='utf-8')
    c.put(out/'manifest.json',dict(inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.TASK/'semantic028.py',diag/'manifest.json']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('Saved11 observations and4 bounded source checks')
if __name__=='__main__':run()
