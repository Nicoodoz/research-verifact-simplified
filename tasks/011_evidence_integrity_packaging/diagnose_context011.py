"""Distinguish literal body anchors from restored structural context anchors."""
from pathlib import Path
import argparse
import study011 as s

def run(out):
    source=s.OUT/'input_diagnostics_001';s.check(source)
    items={r['case_id']:r for r in s.pilot.jsonl(s.OUT/'offline_003/inputs.jsonl')}
    views={r['passage_id']:r['views'] for r in s.pilot.jsonl(s.OUT/'offline_003/views.jsonl')}
    rows=[]
    for x in s.read_json(source/'existing_anchor_lookup.json'):
        row=dict(x);row['body_hits']=row.pop('hits');item=items[x['case_id']]
        quote=' '.join(x['quote'].split())
        row['context_hits']={a:[dict(passage_id=k,context=h) for k in item['retrieval'][a]['selected_ids']
            if views[k][a]['note_id']==x['source_note_id'] for h in views[k][a].get('source_context',[]) if quote in ' '.join(h['text'].split())] for a in s.METHODS}
        row['caveat']='Body and structural context reported separately; absence from body alone does not mean absent from actual Judge reference. Not gold recall.'
        rows.append(row)
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(out/'anchors.json',rows)
    s.seal(out,[source/'manifest.json',s.OUT/'offline_003/manifest.json'],[Path(__file__)])
    print('Separated body/context anchors',len(rows))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=s.OUT/'input_context_diagnostics_001')
    run(ap.parse_args().output)
