"""Full outputs and exact-layout reference reading; no whitespace normalization."""
from pathlib import Path
import argparse,re
import study013 as s
sys_path=s.ROOT/'tasks/010_verifact_baseline_alignment'
import sys
sys.path.insert(0,str(sys_path))
from inspect_references import blocks

def view(case,arms,part,ledger_path=None):
    item=next(r for r in s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl') if r['case_id']==case)
    print(case,item['author_type'],item['subject_id'],item['text'])
    row=next(r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/transitions.jsonl') if r['case_id']==case)
    print('GT',row['human_gt'],{a:row[a] for a in arms})
    if part=='outputs':
        values={r['request_id']:r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/normalized_responses.jsonl')}
        assignments=s.pilot.read_csv(s.OUT/'screen_judge_preparation_001/assignments.csv')[1]
        for a in assignments:
            if a['case_id']==case and a['arm'] in arms and a['round']=='0':
                print('\n',a['arm'],a['request_id']);print(values[a['request_id']].get('output_text','FAILED'))
    else:
        ledger=s.read_json(ledger_path) if ledger_path and ledger_path.exists() else {}
        relevant={a:set() for a in arms}
        if part=='delta':
            values={r['request_id']:r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/normalized_responses.jsonl')}
            for a in s.pilot.read_csv(s.OUT/'screen_judge_preparation_001/assignments.csv')[1]:
                if a['case_id']==case and a['arm'] in arms and a['round']=='0':
                    try:obj=s.pilot.strict_json(values[a['request_id']]['output_text'])
                    except (KeyError,ValueError):continue
                    for check in obj.get('checks',[]):relevant[a['arm']].update(check.get('evidence_ids',[]))
            collections={a:blocks(item['retrieval'][a]['reference']) for a in arms}
            signatures={a:{re.sub(r'^\d+\.\s','',b['raw_block'],count=1) for b in bs} for a,bs in collections.items()}
            common=set.intersection(*signatures.values())
            for a,bs in collections.items():relevant[a]|={b['number'] for b in bs if re.sub(r'^\d+\.\s','',b['raw_block'],count=1) not in common}
        for arm in arms:
            ref=item['retrieval'][arm]['reference'];print('\n',arm,ref.split('1. Date:')[0])
            same=[]
            for b in blocks(ref):
                if part=='delta' and b['number'] not in relevant[arm]:continue
                exact=re.sub(r'^\d+\.\s','',b['raw_block'],count=1)
                key=s.pilot.fingerprint([item['subject_id'],exact])
                if key in ledger:same.append(str(b['number'])+'='+ledger[key])
                else:print(b['raw_block']);ledger[key]=case+'/'+arm+'/'+str(b['number'])
            print('EXACT LAYOUT PREVIOUSLY READ:',','.join(same))
            if part=='delta':print('READ SCOPE: union of actually changed blocks and model-cited blocks; not all reference blocks')
        if ledger_path:
            ledger_path.parent.mkdir(parents=True,exist_ok=True);ledger_path.write_text(s.pilot.canonical(ledger)+'\n',encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('part',choices=('outputs','inputs','delta'))
    p.add_argument('--arms',nargs='+',required=True);p.add_argument('--ledger',type=Path);a=p.parse_args()
    view(a.case,a.arms,a.part,a.ledger)
