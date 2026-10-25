"""Render manually read cases with exact quotes; no automatic medical adjudication."""
import argparse
from pathlib import Path
import common014 as c

def render(out):
    c.require(not out.exists(),'Review output exists')
    source=c.OUT/'analysis_001'
    selected=c.csvrows(source/'selected_cases.csv')
    notes=c.read(c.TASK/'case_notes.json')
    c.require({r['case_id'] for r in selected}=={r['case_id'] for r in notes},'Reading coverage differs')
    c.require(len(notes)==len({r['case_id'] for r in notes}),'Duplicate reading case')
    out.mkdir(parents=True);anchors=[];index=[]
    for note in notes:
        packet=c.read(source/'cases'/(note['case_id']+'.json'))
        r=packet['row']
        text=[f"# {r['case_id']}：{note['title']}",f"作者：{r['author_type']}；GT：{r['human_gt']}；V4：{r['baseline']}；Qwen：{r['qwen']}；转移：{r['movement']}",
            '## 直接观察',note['observation'],'## 解释假设与边界',note['interpretation'],note['uncertainty'],'## 可回查摘录']
        for q in note['quotes']:
            value=packet[q['field']];quote=q['text'];start=value.find(quote)
            c.require(start>=0,'Quote not present '+r['case_id']+' '+q['field'])
            anchors.append(dict(case_id=r['case_id'],field=q['field'],text=quote,start=start,end=start+len(quote),
                source_sha256=c.pilot.digest_text(value)))
            text.append(f"- {q['field']} [{start},{start+len(quote)}): {quote}")
        for field,title in [('claim','原命题'),('reference','完整实际C48 reference'),('v4_output','V4完整输出'),('qwen_output','Qwen完整输出')]:
            text += ['## '+title,'```text',packet[field],'```']
        (out/(r['case_id']+'.md')).write_text('\n\n'.join(text)+'\n',encoding='utf-8',newline='\n')
        index.append(dict(case_id=r['case_id'],author=r['author_type'],movement=r['movement'],primary_observation=note['category'],
            scope='purpose-sampled executor observation; not medical GT or causal diagnosis'))
    c.write_json(out/'anchors.json',anchors);c.write_csv(out/'case_index.csv',index)
    c.write_json(out/'notes_snapshot.json',notes)
    c.write_json(out/'coverage.json',dict(cases=len(notes),complete_claim_reference_and_both_outputs_read=True,
        independent_medical_adjudication=False,causal_intervention=False,quotes=len(anchors),
        categories='descriptive observations only; cannot estimate population mechanism prevalence'))
    c.write_json(out/'manifest.json',dict(created_utc=c.now(),files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in out.iterdir() if p.is_file()},
        dependencies={str((c.TASK/'case_notes.json').relative_to(c.ROOT)):c.file_hash(c.TASK/'case_notes.json'),
                      str((source/'manifest.json').relative_to(c.ROOT)):c.file_hash(source/'manifest.json')},
        code_sha256={str(Path(__file__).relative_to(c.ROOT)):c.file_hash(Path(__file__))}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'review_001');render(p.parse_args().output.resolve())
