"""Read complete outputs or references, with exact-block reading reuse."""
from pathlib import Path
import argparse
import study012 as s
from inspect_references import blocks,normalized

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('case');ap.add_argument('part',choices=('outputs','inputs','source'));ap.add_argument('--ledger',type=Path)
    a=ap.parse_args();p=next(x for x in s.pilot.jsonl(s.OUT/'materials_001/packets.jsonl') if x['row']['case_id']==a.case)
    r=p['row'];print(r['case_id'],r['author_type'],r['subject_id'],'GT',r['human_gt'],'O/V/C',r['O'],r['V'],r['C'],'CLAIM',r['text'])
    if a.part=='outputs':
        for field in ('reason','reasoning_chain','reasoning_final_answer'):print('\nORIGINAL',field,'\n',p['original'][field])
        for label,key in [('V','verifact_reference'),('C','c48_reference')]:print('\nFULL',label,'\n',p['current_outputs'][key]['output_text'])
    if a.part=='source':
        print('PARENT:',p['proposition']['parent_text_chunk']);print('HUMAN:',p['human']);print('VALIDITY:',p['validity'])
    if a.part=='inputs':
        ledger=s.read_json(a.ledger) if a.ledger and a.ledger.exists() else {}
        for arm,ref in p['input']['references'].items():
            print('\nREFERENCE',arm,ref[:ref.index('1. Date: ')])
            same=[]
            for b in blocks(ref):
                key=s.pilot.fingerprint([r['subject_id'],b['date'],b['time'],b['category'],b['description'],b['note_id'],normalized(b['text'])])
                if key in ledger:same.append(str(b['number'])+'='+ledger[key])
                else:print(b['raw_block']);ledger[key]=a.case+'/'+arm+'/'+str(b['number'])
            print('IDENTICAL ALREADY READ:',','.join(same))
        if a.ledger:
            a.ledger.parent.mkdir(parents=True,exist_ok=True);a.ledger.write_text(s.pilot.canonical(ledger)+'\n',encoding='utf-8')
