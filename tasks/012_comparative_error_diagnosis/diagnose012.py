"""Assemble executor diagnosis, literal anchors and unchanged unified scores."""
import argparse,json,re
from pathlib import Path
from collections import Counter
import study012 as s

NOTE_FILES=[s.TASK/x for x in ('notes_working.json','notes_batch002.json','notes_batch003.json')]

def anchor_text(packet,a):
    if a['kind']=='parent':return packet['proposition']['parent_text_chunk']
    if a['kind']=='human':return packet['human'][a['field']]
    if a['kind']=='reference':return packet['input']['references'][{'V':'verifact_reference','C':'c48_reference'}[a['system']]]
    if a['system']=='O':return packet['original'][a.get('field','reasoning_final_answer')]
    return packet['current_outputs'][{'V':'verifact_reference','C':'c48_reference'}[a['system']]]['output_text']

def locate(text,quote):
    # Exact literal quotation only. Do not silently relax punctuation/case or fabricate offsets.
    return [m.start() for m in re.finditer(re.escape(quote),text)]

def load_notes(packets):
    notes=[n for f in NOTE_FILES for n in s.read_json(f)['cases']]
    assert len(notes)==len({n['case_id'] for n in notes})==24
    problems=[]
    for n in notes:
        assert set(n['layers'])<=set(s.LAYERS) and set(n['mechanisms'])<=set(s.MECHANISMS)
        for a in n['anchors']:
            txt=anchor_text(packets[n['case_id']],a);positions=locate(txt,a['quote'])
            if not positions:problems.append((n['case_id'],a))
            a['positions']=[[x,x+len(a['quote'])] for x in positions];a['source_text_sha256']=s.pilot.digest_text(txt)
    assert not problems,json.dumps(problems,ensure_ascii=False,indent=2)
    return {n['case_id']:n for n in notes}

def build(out):
    for name in ('alignment_002','materials_001','pipeline_001','raw_search_001'):s.check(s.OUT/name)
    rows=s.pilot.jsonl(s.OUT/'alignment_002/ledger.jsonl')
    packets={p['row']['case_id']:p for p in s.pilot.jsonl(s.OUT/'materials_001/packets.jsonl')}
    notes=load_notes(packets)
    selected=set(s.read_json(s.OUT/'alignment_002/summary.json')['selected_cases'])
    assert set(notes)==selected
    raw_summary={r['case_id']:r for r in s.read_json(s.OUT/'raw_search_001/summary.json')}
    raw_anchors=s.read_json(s.OUT/'raw_search_001/anchors.json')
    metrics={};patient=[];class_rows=[]
    for author in ('llm','human'):
        own=[r for r in rows if r['author_type']==author];metrics[author]={}
        for system in s.SYSTEMS:
            value=s.pilot.evaluate(own,[dict(proposition_id=r['proposition_id'],verdict=r[system]) for r in own],profile='none')
            metrics[author][system]=value
        for gt in ('Supported','Not Supported','Not Addressed'):
            group=[r for r in own if r['human_gt']==gt]
            class_rows.append(dict(author_type=author,human_gt=gt,n=len(group),**{x:dict(Counter(r[x] for r in group)) for x in s.SYSTEMS}))
        for sid in sorted({r['subject_id'] for r in own}):
            group=[r for r in own if r['subject_id']==sid]
            patient.append(dict(author_type=author,subject_id=sid,n=len(group),
                **{x:sum(r[x]==r['human_gt'] for r in group) for x in s.SYSTEMS},
                **{pair:dict(Counter(r[pair] for r in group)) for pair in ('O_to_C','O_to_V','V_to_C')}))
    for r in rows:
        n=notes.get(r['case_id'])
        r['semantic_review_status']='deep_read_complete_executor' if n else ('prior_task_only_not_deep_read_012' if r['prior_case_membership'] else 'not_deep_read_012')
        r['diagnostic_layers']=n['layers'] if n else []
        r['mechanism_hypotheses']=n['mechanisms'] if n else []
        r['diagnosis_entry']='cases/'+r['case_id']+'.md' if n else ''
        r['machine_checks']='650 alignment/full output mapping/final JSON/C48 reconstruction'
        r['unknown_is_not_no_problem']=True
        r['layer_review']={layer:('semantic_observation_with_uncertainty' if n and layer in n['layers'] else 'not_semantically_attributed') for layer in s.LAYERS}
        r['original_upstream_status']='unavailable_candidate_logs; never imputed from C48'
    out.mkdir(parents=True,exist_ok=False);(out/'cases').mkdir()
    for cid,n in notes.items():
        p=packets[cid];r=p['row']
        n.update(dict(full_claim_parent_doctor_fields_read=True,full_O_chain_final_V_C_outputs_read=True,
            both_references_all_blocks_read=True,reference_reading_method='exact block dedup across same patient, with metadata retained',
            raw_search=raw_summary[cid],raw_search_hits_are_not_all_semantically_reviewed=True,
            independent_semantic_check=cid in {'N086','N095','N139','N182','N188','N264','N388','N395','N501','N526','N578'}))
        lines=[f'# {cid} 对照诊断',f"\n{r['author_type']} / 患者 {r['subject_id']} / GT={r['human_gt']} / O,V,C={r['O']}, {r['V']}, {r['C']}",
            '\n原claim：'+r['text'],'\n执行者诊断，不是医学GT；定向独立核查不等于全任务审计。',
            '\n问题位置：'+', '.join(n['layers']),'\n机制假设：'+', '.join(n['mechanisms'])]
        for k,label in [('observation','直接观察'),('interpretation','可能解释'),('counterevidence','反证、替代与互补材料'),('uncertainty','不能确定')]:lines+=['\n## '+label+'\n',n[k]]
        lines+=['\n## 字面锚点（对应完整文本的字符位置）\n','```json',json.dumps(n['anchors'],ensure_ascii=False,indent=2),'```',
            '\n## 原EHR有限查找范围\n',json.dumps(raw_summary[cid],ensure_ascii=False),'\n所有命中见 ../../raw_search_001/matches.jsonl；命中不代表充分，零命中不代表临床不存在。']
        for a in raw_anchors:
            if a['case_id']==cid:lines+=['\n### 原文到C48的保存轨迹\n','```json',json.dumps(a,ensure_ascii=False,indent=2),'```']
        lines+=['\n## 原来源与医生记录\n','来源只用于诊断命题理解，没有进入本任务任何新Judge，也不能作为自证依据。',p['proposition']['parent_text_chunk'],'```json',json.dumps(p['human'],ensure_ascii=False,indent=2),'```',
            '\n## 三组完整生成输出\n']
        for field in ('reason','reasoning_chain','reasoning_final_answer'):lines+=['\n### O / '+field+'\n',p['original'][field] or '']
        for name,key in [('V','verifact_reference'),('C','c48_reference')]:lines+=['\n### '+name+'\n',p['current_outputs'][key]['output_text']]
        for key,text in p['input']['references'].items():lines+=['\n## 完整实际reference / '+key+'\n',text]
        (out/'cases'/f'{cid}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    s.pilot.write_json(out/'diagnoses.json',list(notes.values()))
    s.pilot.write_jsonl(out/'ledger.jsonl',rows);s.pilot.write_csv(out/'ledger.csv',rows)
    s.pilot.write_jsonl(out/'error_union.jsonl',[r for r in rows if r['error_union']])
    s.pilot.write_jsonl(out/'all_three_correct.jsonl',[r for r in rows if r['correctness_pattern']=='111'])
    s.pilot.write_json(out/'metrics.json',metrics);s.pilot.write_json(out/'class_transitions.json',class_rows)
    s.pilot.write_json(out/'patient_transitions.json',patient)
    summary=dict(claims=650,error_union=195,all_three_correct=455,deep_cases=24,
        deep_error_union=sum(r['error_union'] for r in rows if r['case_id'] in notes),
        deep_all_three_correct=sum(r['correctness_pattern']=='111' for r in rows if r['case_id'] in notes),
        unreviewed_error_union=sum(r['error_union'] for r in rows if r['case_id'] not in notes),
        status_counts=dict(Counter(r['semantic_review_status'] for r in rows)),new_api_calls=0,cost_cny=0,
        independent_audit='pending; bounded semantic/machine independent checks only')
    s.pilot.write_json(out/'summary.json',summary)
    s.seal(out,[s.OUT/x/'manifest.json' for x in ('alignment_002','materials_001','pipeline_001','raw_search_001')]+NOTE_FILES,[Path(__file__)])
    print(s.pilot.canonical(summary))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=s.OUT/'diagnosis_001')
    build(ap.parse_args().output)
