"""Read complete references, optionally reusing already read identical fact blocks.

The ledger is a reading aid only: every occurrence and its exact original block
is retained in reference_diagnostics_001/blocks.jsonl and preparation_001.
"""
from pathlib import Path
import argparse
import alignment_common as s
from inspect_references import blocks,normalized


def show(case_id,ledger=None,only_arm=None):
    item=next(x for x in s.pilot.jsonl(s.OUT/'preparation_001/inputs.jsonl') if x['case_id']==case_id)
    prior=s.read_json(ledger) if ledger and ledger.exists() else {}
    print('CASE',case_id,item['author_type'],item['subject_id'],'CLAIM',item['text'])
    for arm,ref in item['references'].items():
        if only_arm and arm!=only_arm:
            continue
        print('\nREFERENCE',arm,'CHARACTERS',len(ref))
        print(ref[:ref.index('1. Date: ')])
        shared=[]
        for b in blocks(ref):
            key=s.pilot.fingerprint([item['subject_id'],b['date'],b['time'],b['category'],b['description'],b['note_id'],normalized(b['text'])])
            if key in prior:
                shared.append(str(b['number'])+'='+prior[key])
            else:
                print(b['raw_block'])
                prior[key]=case_id+'/'+arm+'/'+str(b['number'])
        print('IDENTICAL_BLOCKS_ALREADY_READ:',','.join(shared))
    if ledger:
        ledger.parent.mkdir(parents=True,exist_ok=True)
        # This is a mutable in-progress reading aid, not an experimental receipt.
        ledger.write_text(s.pilot.canonical(prior)+'\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('case')
    p.add_argument('--ledger',type=Path)
    p.add_argument('--arm',choices=s.METHODS)
    a=p.parse_args()
    show(a.case,a.ledger,a.arm)
