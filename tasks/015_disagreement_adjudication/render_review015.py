"""Render executor observations and exact quotes with all four outputs, not medical GT."""
from pathlib import Path
import argparse
import common015 as c

def render(out):
    c.require(not out.exists(),'Review exists')
    notes=c.read(c.TASK/'case_notes.json');selected=c.csvrows(c.OUT/'analysis_001/selected_cases.csv')
    c.require(len(notes)==len({r['case_id'] for r in notes}) and {r['case_id'] for r in notes}=={r['case_id'] for r in selected},'Coverage mismatch')
    out.mkdir(parents=True);anchors=[];index=[]
    for note in notes:
        p=c.read(c.OUT/'analysis_001/cases'/(note['case_id']+'.json'));r=p['row']
        lines=[f"# {r['case_id']}：{note['title']}",c.canonical(r),'## 直接观察',note['observation'],
            '## 解释与限制',note['interpretation'],note['uncertainty'],'## 可回查引用']
        for q in note['quotes']:
            v=p[q['field']];start=v.find(q['text']);c.require(start>=0,'Absent quote '+r['case_id']+' '+q['field'])
            anchors.append(dict(case_id=r['case_id'],field=q['field'],text=q['text'],start=start,end=start+len(q['text']),source_sha256=c.pilot.digest_text(v)))
            lines.append(q['field']+': '+q['text'])
        for field in ('claim','reference','v4_output','qwen_output','adjudication_output','evidence_only_output'):
            lines+=['## '+field,'```text',p[field],'```']
        (out/(r['case_id']+'.md')).write_text('\n\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
        index.append(dict(case_id=r['case_id'],author=r['author_type'],bucket=r['bucket'],adjudication_correct=r['adjudication']==r['human_gt'],category=note['category']))
    c.write_json(out/'anchors.json',anchors);c.write_csv(out/'case_index.csv',index);c.write_json(out/'notes_snapshot.json',notes)
    c.write_json(out/'coverage.json',dict(cases=len(notes),quotes=len(anchors),complete_claim_reference_and_four_outputs_read=True,
        new_medical_gt=False,causal_mechanism_proof=False,purpose_sample_not_prevalence_estimate=True))
    c.write_json(out/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in out.iterdir() if p.is_file()},
        dependencies={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in [c.TASK/'case_notes.json',c.OUT/'analysis_001/manifest.json',Path(__file__)]}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'review_001');render(p.parse_args().output.resolve())
