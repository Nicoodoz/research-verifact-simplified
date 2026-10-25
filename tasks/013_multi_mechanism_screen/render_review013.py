"""Bind executor observations to exact references/outputs; no new medical labels."""
from pathlib import Path
import json,re,argparse
import study013 as s

def run(out=None):
    out=out or s.OUT/'review_final_001'
    files=sorted(s.TASK.glob('review_notes_*.json'))
    notes=[n for f in files for n in s.read_json(f)['cases']]
    assert len(notes)==len({n['case_id'] for n in notes})==35
    selected=s.read_json(s.OUT/'review_001/selection.json')
    assert {(n['case_id'],a) for n in notes for a in n['arms']}=={(r['case_id'],r['arm']) for r in selected}
    inputs={x['case_id']:x for x in s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl')}
    rows={r['case_id']:r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/transitions.jsonl')}
    values={r['request_id']:r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/normalized_responses.jsonl')}
    assignments=s.pilot.read_csv(s.OUT/'screen_judge_preparation_001/assignments.csv')[1]
    mapped={(a['case_id'],a['arm']):a for a in assignments if a['round']=='0'}
    bad=[];count=0;unique=set()
    for n in notes:
        cid=n['case_id']
        arms=set(n['arms'])|{a['arm'] for a in n['anchors']}|{'baseline'}
        if 'wide_candidates' in arms:arms.add('refresh48')
        n['display_arms']=sorted(arms)
        n['reading_scope']='Complete outputs for displayed arms; changed and cited reference blocks, with exact-layout reuse; full references preserved below, not all necessarily re-read'
        if cid in ('N144','N580'):n['reading_scope']+='; full baseline and compared references additionally read'
        if cid=='N529':n['reading_scope']+='; full baseline additionally read'
        for arm in arms:unique.add(mapped[(cid,arm)]['request_id'])
        for a in n['anchors']:
            text=inputs[cid]['retrieval'][a['arm']]['reference'] if a['kind']=='reference' else values[mapped[(cid,a['arm'])]['request_id']]['output_text']
            hits=[m.start() for m in re.finditer(re.escape(a['quote']),text)]
            if not hits:bad.append([cid,a['arm'],a['kind'],a['quote']])
            a['positions']=[[i,i+len(a['quote'])] for i in hits];a['source_sha256']=s.pilot.digest_text(text);count+=1
    assert not bad,json.dumps(bad,ensure_ascii=False,indent=2)
    out.mkdir(parents=True,exist_ok=False);(out/'cases').mkdir()
    for n in notes:
        cid=n['case_id'];x=inputs[cid];r=rows[cid]
        lines=[f'# {cid} 013定向对照',f"\n{x['author_type']} / 患者{x['subject_id']} / 原GT={r['human_gt']}",
            '\n原claim：'+x['text'],'\n阅读范围：'+n['reading_scope'],
            '\n执行者观察，不是新增医学GT或独立审计结论。']
        for key,title in [('observation','直接观察'),('interpretation','可能解释'),('counterevidence','反证与替代/互补材料'),('uncertainty','不确定性')]:lines+=['\n## '+title+'\n',n[key]]
        lines+=['\n## 逐字锚点\n','```json',json.dumps(n['anchors'],ensure_ascii=False,indent=2),'```']
        for arm in n['display_arms']:
            a=mapped[(cid,arm)];v=values[a['request_id']]
            lines+=['\n## '+arm+' / '+str(r[arm])+'\n','完整请求：'+a['request_id'],'\n### 完整输出\n',v['output_text'],
                '\n### 完整实际reference（保存供复查）\n',x['retrieval'][arm]['reference']]
        (out/'cases'/f'{cid}.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    s.pilot.write_json(out/'notes.json',notes)
    s.pilot.write_json(out/'coverage.json',dict(cases=35,selected_comparisons=37,complete_unique_output_reads=len(unique),
        quote_anchors=count,full_reference_claim=False,whitespace_normalized_for_reading=False,
        not_method_error_prevalence=True,independent_audit=False))
    s.freeze(out,[s.OUT/'review_001/selection.json',s.OUT/'screen_inputs_001/manifest.json',s.OUT/'screen_analysis_001/normalized_responses.jsonl',*files],[Path(__file__)])
    print(s.pilot.canonical(s.read_json(out/'coverage.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();run(a.output)
