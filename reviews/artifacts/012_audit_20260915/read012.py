from pathlib import Path
import json,sys,re
O=Path('D:/Research-VeriFact/outputs/012_comparative_error_diagnosis')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
packets={p['row']['case_id']:p for p in jl(O/'materials_001/packets.jsonl')}
if sys.argv[1]=='notes':
    for d in read(O/'diagnosis_001/diagnoses.json')[int(sys.argv[2]):int(sys.argv[3])]:
        print(d['case_id'],packets[d['case_id']]['row']['text'])
        for k in ('observation','interpretation','counterevidence','uncertainty'):print(k+':',d[k])
elif sys.argv[1]=='sizes':
    for cid,p in packets.items():print(cid,len(p['original']['reasoning_chain'] or ''),len(p['original']['reasoning_final_answer'] or ''),sum(len(x['output_text']) for x in p['current_outputs'].values()))
else:
    for cid in sys.argv[2:]:
        p=packets[cid];r=p['row'];print('CASE',cid,'GT',r['human_gt'],'O/V/C',r['O'],r['V'],r['C'],'CLAIM',r['text'])
        if sys.argv[1]=='source':
            print('PARENT',p['proposition']['parent_text_chunk']);print('HUMAN',json.dumps(p['human'],ensure_ascii=False));print('VALIDITY',json.dumps(p['validity'],ensure_ascii=False))
        if sys.argv[1]=='outputs':
            for k in ('reasoning_chain','reasoning_final_answer'):print('O',k,p['original'][k])
            for arm,v in p['current_outputs'].items():print(arm,v['output_text'])
