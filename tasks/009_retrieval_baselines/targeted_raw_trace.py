"""Bounded source follow-up to reviewed cases, not a medical retrieval gold set."""
from collections import Counter
from pathlib import Path
import re
import study009 as s


def run():
    folder=s.OUT/'confirmation_001'
    items={x['case_id']:x for x in s.pilot.jsonl(folder/'judge_preparation/inputs.jsonl')}
    corpus=s.pilot.jsonl(folder/'preparation/corpus.jsonl')
    specifications=[('N071',dict(notes=['99065'])),('N561',dict(notes=['1088126'])),
        ('N405',dict(dates=['[CLINICAL_LITERAL_REMOVED]'],pattern=r'bronch|mucous|mucus|RLL|right lower')),
        ('N585',dict(dates=['[CLINICAL_LITERAL_REMOVED]'],pattern=r'RLL|right lower|bronch')),
        ('N343',dict(dates=['[CLINICAL_LITERAL_REMOVED]'],pattern=r'resus|transf|ICU'))]
    result=[]
    for cid,spec in specifications:
        own=[p for p in corpus if p['subject_id']==items[cid]['subject_id']]
        selected=[p for p in own if (p['note_id'] in spec['notes'] if 'notes' in spec else p['date'] in spec['dates'] and re.search(spec['pattern'],p['text'],re.I))]
        result.append(dict(case_id=cid,search_specification=spec,meaning='literal bounded follow-up, not exhaustive semantic absence',
            date_note_counts={d:len({p['note_id'] for p in own if p['date']==d}) for d in spec.get('dates',[])},passages=selected))
        print('\nFOLLOWUP',cid,spec,'matched',len(selected))
        seen=set()
        for p in selected:
            if p['text'] in seen:
                print('EXACT DUPLICATE',p['note_id'],p['start'])
                continue
            seen.add(p['text'])
            print('NOTE',p['note_id'],p['date'],p['start'],p['end_exclusive'])
            print(p['text'])
    out=folder/'targeted_trace_001'
    out.mkdir(exist_ok=False)
    s.pilot.write_json(out/'records.json',result)
    s.seal(out,[folder/'preparation/manifest.json',folder/'judge_preparation/manifest.json'],[Path(__file__)])


if __name__=='__main__':
    run()
