"""Materialize exact inputs, full outputs and evidence changes for audit reading."""
from pathlib import Path
import argparse
import study011 as s

def build(phase,out):
    off=s.OUT/'offline_003';analysis=s.OUT/f'{phase}_analysis_001'
    s.check(off);s.check(analysis)
    items={x['proposition_id']:x for x in s.pilot.jsonl(off/'inputs.jsonl')}
    views={x['passage_id']:x['views'] for x in s.pilot.jsonl(off/'views.jsonl')}
    responses={r['request_id']:r for r in s.pilot.jsonl(analysis/'normalized_responses.jsonl')}
    aa=s.pilot.read_csv(s.OUT/f'{phase}_preparation_001/assignments.csv')[1]
    cohort={r['proposition_id']:r for r in s.pilot.read_csv(off/'cohort.csv')[1]}
    selected=s.read_json(off/'pilot_selection.json')
    packets=[]
    for pid,item in items.items():
        if item['case_id'] not in selected:continue
        assignments=[a for a in aa if a['proposition_id']==pid]
        union={k for r in item['retrieval'].values() for k in r['selected_ids']}
        packets.append(dict(case_id=item['case_id'],input=item,human_gt=cohort[pid]['human_gt'],selection=selected[item['case_id']],
            views={k:views[k] for k in sorted(union)},outputs=[dict(arm=a['arm'],round=int(a['round']),**{'response':responses[a['request_id']]}) for a in assignments]))
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'packets.jsonl',packets)
    s.pilot.write_json(out/'summary.json',dict(cases=len(packets),logical_outputs=sum(len(p['outputs']) for p in packets),phase=phase))
    s.seal(out,[off/'manifest.json',analysis/'manifest.json'],[Path(__file__)])
    print('Review cases',len(packets))

def show(folder,cid,part):
    packet=next(p for p in s.pilot.jsonl(folder/'packets.jsonl') if p['case_id']==cid)
    item=packet['input'];print(cid,packet['human_gt'],item['text'])
    if part=='inputs':
        # Each view has raw offsets; B contains A literally. Show union of actual views.
        for k,v in packet['views'].items():
            members={a:item['retrieval'][a]['selected_ids'].index(k)+1 for a in s.METHODS if k in item['retrieval'][a]['selected_ids']}
            print('\nPASSAGE',k,'ARMS/NUMBER',members)
            print('NOTE',v['A']['note_id'],v['A']['date'],v['A']['time'],v['A']['category'],v['A']['description'])
            a,b=v['A'],v['B'];print('A raw span',a['start'],a['end_exclusive'],'B/C raw span',b['start'],b['end_exclusive'])
            if 'B' in members or 'C' in members:print('B/C FULL TEXT:',b['text'])
            else:print('A FULL TEXT:',a['text'])
            if 'C' in members:print('C literal context:',v['C']['source_context'])
    if part=='outputs':
        seen=set()
        for o in packet['outputs']:
            r=o['response'];print('\nARM',o['arm'],'ROUND',o['round'],'STATUS',r['status'],'VERDICT',r.get('verdict'))
            if r['request_id'] not in seen:
                print(r['output_text']);seen.add(r['request_id'])
            else:print('Same complete request/response as above; cached by preregistered body.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('build','show'));p.add_argument('phase',choices=s.STAGE_CAPS)
    p.add_argument('--case');p.add_argument('--part',choices=('inputs','outputs'));p.add_argument('--output',type=Path)
    a=p.parse_args();folder=a.output or s.OUT/f'{a.phase}_review_001'
    if a.action=='build':build(a.phase,folder)
    else:show(folder,a.case,a.part)
