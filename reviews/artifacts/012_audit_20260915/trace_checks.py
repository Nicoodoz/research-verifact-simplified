"""Independent raw-source/pipeline probes and selected complete reference display."""
from pathlib import Path
import json,re
R=Path('D:/Research-VeriFact');O=R/'outputs/012_comparative_error_diagnosis';T=Path(__file__).resolve().parent
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
packets={p['row']['case_id']:p for p in jl(O/'materials_001/packets.jsonl')};notes={p['ROW_ID']:p for p in jl(O/'materials_001/ehr_notes.jsonl')};corpus=jl(O/'materials_001/corpus.jsonl')
details=[]
for cid,nid,lo,hi in [('N086','375697',12108,12117),('N395','564621',4589,4646),('N395','564631',4589,4646),('N526','476451',927,949),('N526','476489',927,949),('N501','473836',546,603),('N578','470821',7854,7916)]:
    p=packets[cid];item=p['C_pipeline'];note=notes[nid];assert note['SUBJECT_ID']==p['row']['subject_id']
    ret=item['retrieval']['C48'];ranks={k:[x[0] for x in item['rankings'][k]] for k in ('dense','bm25')};ranks['hybrid']=item['rankings']['hybrid'];ranks['candidate']=ret['candidate_ids'];ranks['rerank']=sorted(ret['candidate_ids'],key=lambda k:(-item['scores'][k],k));ranks['selected']=ret['selected_ids']
    found=[]
    for block in corpus:
        if block['note_id']!=nid or block['start']>=hi or block['end_exclusive']<=lo:continue
        k=block['passage_id'];assert block['text']==note['TEXT'][block['start']:block['end_exclusive']]
        found.append({'passage_id':k,'span':[block['start'],block['end_exclusive']],**{route:(v.index(k)+1 if k in v else None) for route,v in ranks.items()},'score':item['scores'].get(k),'skip':next((x['reason'] for x in ret['selection_skips'] if x['passage_id']==k),None)})
    details.append({'case_id':cid,'note_id':nid,'anchor':[lo,hi],'text':note['TEXT'][lo:hi],'chartdate':note['CHARTDATE'],'charttime':note['CHARTTIME'],'blocks':found})
    if cid=='N086':
        assert note['TEXT'][lo:hi]=='No nausea';positive=next(x for x in found if x['span'][0]==12111)
        assert positive['candidate']==8 and positive['rerank']==1 and positive['selected'] is not None
        assert any(x['dense']==52 and x['candidate'] is None for x in found)
    if cid=='N395': assert all(x['skip']=='character_cap' and x['candidate'] is not None and x['rerank'] in (21,22) and x['selected'] is None for x in found)
    if cid=='N526':assert all(x['bm25'] in (79,80) and x['hybrid'] in (140,142) and x['dense'] is None and x['candidate'] is None and x['score'] is None for x in found)
(T/'raw_trace_checks.json').write_text(json.dumps(details,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(details,ensure_ascii=False,indent=2))
for cid,pattern in [('N086',r'No nausea|N/V|nausea, no abdominal'),('N395',r'Consults|F/u Ortho|per ortho'),('N526',r'[CLINICAL_LITERAL_REMOVED]|76 - 107|81 - 103|improved'),('N501',r'Abdominal CT|f/u CT|CT Results|CT with contrast'),('N578',r'low U/O|lasix held|hold lasix')]:
    p=packets[cid];print('CASE',cid)
    for arm,ref in p['input']['references'].items():
        print('REFERENCE',arm)
        for b in re.split(r'(?m)(?=^\d+\. Date: )',ref):
            if re.search(pattern,b,re.I):print(b)
