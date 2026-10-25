"""Validate executor observations against exact complete inputs and responses."""
from pathlib import Path
import re
import argparse
import study011 as s

def render(phase,notes_file,out):
    review=s.OUT/f'{phase}_review_001';s.check(review)
    packets={r['case_id']:r for r in s.pilot.jsonl(review/'packets.jsonl')}
    notes=s.read_json(notes_file);anchors=[];pages=[]
    for note in notes['cases']:
        cid=note['case_id'];p=packets[cid];item=p['input']
        for raw in note['anchors']:
            a=dict(raw,case_id=cid)
            if a.get('kind','reference')=='reference':
                text=item['retrieval'][a['arm']]['reference']
                a['reference_sha256']=s.pilot.digest_text(text)
            else:
                result=next(o['response'] for o in p['outputs'] if o['arm']==a['arm'] and o['round']==a['round'])
                text=result['output_text'];a['request_id']=result['request_id']
            assert a['quote'] and a['quote'] in text,(cid,a)
            a['sha256']=s.pilot.digest_text(text)
            a['quote_spans']=[[m.start(),m.end()] for m in re.finditer(re.escape(a['quote']),text)]
            anchors.append(a)
        page=[f'# {cid}：执行者诊断（非医学GT）',item['text'],'原GT：'+p['human_gt'],
            '直接观察：'+note['observation'],'可能解释：'+note['interpretation'],'不确定：'+note['uncertainty']]
        for arm in s.METHODS:
            page+=['## '+arm+' 完整reference','```text\n'+item['retrieval'][arm]['reference']+'\n```']
            for o in p['outputs']:
                if o['arm']==arm:page+=['### 第'+str(o['round'])+'轮完整输出','```json\n'+str(o['response'].get('output_text'))+'\n```']
        pages.append((cid,'\n\n'.join(page)+'\n'))
    out.mkdir(parents=True,exist_ok=False);(out/'cases').mkdir()
    for cid,text in pages:(out/'cases'/(cid+'.md')).write_text(text,encoding='utf-8')
    s.pilot.write_json(out/'notes_snapshot.json',notes)
    s.pilot.write_json(out/'anchors.json',anchors)
    s.pilot.write_json(out/'summary.json',dict(read_cases=len(pages),literal_anchors=len(anchors),not_new_medical_gt=True))
    s.seal(out,[review/'manifest.json',notes_file],[Path(__file__)])
    print('Rendered cases',len(pages),'anchors',len(anchors))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=s.STAGE_CAPS);p.add_argument('notes',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();render(a.phase,a.notes.resolve(),a.output.resolve())
