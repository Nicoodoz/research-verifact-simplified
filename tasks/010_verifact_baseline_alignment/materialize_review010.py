"""Validate literal notes against full reference/output, then preserve review pages."""
from pathlib import Path
import re
import argparse
import alignment_common as s
from inspect_references import blocks


def render(notes_file,output):
    packets={p['row']['case_id']:p for p in s.pilot.jsonl(s.OUT/'review_002/packets.jsonl')}
    notes=s.read_json(notes_file)
    assert {n['case_id'] for n in notes['cases']}==set(packets)
    anchors=[];pages=[]
    for note in notes['cases']:
        cid=note['case_id'];p=packets[cid];item=p['input'];row=p['row']
        for aa in note['anchors']:
            a=dict(aa,case_id=cid)
            if a.get('kind','reference')=='reference':
                ref=item['references'][a['arm']]
                b=next(x for x in blocks(ref) if x['number']==a['block'])
                text=b['raw_block']
                a.update(reference_sha256=s.pilot.digest_text(ref),reference_block_start=b['start'],reference_block_end=b['end_exclusive'])
            else:
                text=p['outputs'][a['arm']]['output_text']
                a['request_id']=p['outputs'][a['arm']]['request_id']
            assert a['quote'] and a['quote'] in text,(cid,a)
            a.update(text_sha256=s.pilot.digest_text(text),quote_spans=[[m.start(),m.end()] for m in re.finditer(re.escape(a['quote']),text)])
            anchors.append(a)
        text=[f'# {cid}：执行者诊断（非医生gold）',item['text'],
            f"原GT={row['human_gt']}；历史发布={p['released_system_verdict']}；旧009 C48={row['old_009_C48']}；本次C48={row['c48_reference']}；本次发布reference={row['verifact_reference']}。",
            '选例：'+'；'.join(p['reasons']),
            '直接观察：'+note['observation'],'可能解释：'+note['interpretation'],'仍不确定：'+note['uncertainty']]
        for arm in s.METHODS:
            text.extend(['## 完整reference：'+arm,'```text\n'+item['references'][arm]+'\n```',
                '## 完整Judge输出：'+arm,'```json\n'+str(p['outputs'][arm].get('output_text'))+'\n```'])
        pages.append((cid,'\n\n'.join(text)+'\n'))
    output.mkdir(parents=True,exist_ok=False)
    (output/'cases').mkdir()
    for cid,text in pages:
        (output/'cases'/(cid+'.md')).write_text(text,encoding='utf-8')
    s.pilot.write_json(output/'notes_snapshot.json',notes)
    s.pilot.write_json(output/'anchors.json',anchors)
    s.pilot.write_json(output/'summary.json',dict(cases=len(pages),anchors=len(anchors),full_Judge_outputs=sum(len(p['outputs']) for p in packets.values()),not_new_clinical_labels=True))
    s.seal(output,[s.OUT/'review_002/manifest.json',notes_file],[Path(__file__),s.TASK/'inspect_references.py'])
    print('Rendered',len(pages),'cases and',len(anchors),'literal anchors')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('notes',type=Path);p.add_argument('--output',type=Path,default=s.OUT/'review_002/semantic_001')
    a=p.parse_args();render(a.notes.resolve(),a.output.resolve())
