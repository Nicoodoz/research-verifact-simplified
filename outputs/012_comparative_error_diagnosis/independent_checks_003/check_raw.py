import hashlib
import json
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
PACKETS = ROOT/'outputs/012_comparative_error_diagnosis/materials_001/packets.jsonl'
CORPUS = ROOT/'outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl'
RAW = ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz'
packets = {r['row']['case_id']:r for r in (json.loads(line) for line in PACKETS.read_text(encoding='utf8').splitlines())}
corpus = [json.loads(line) for line in CORPUS.read_text(encoding='utf8').splitlines()]
db = duckdb.connect()
query = db.execute('SELECT * FROM read_csv_auto(?,all_varchar=true) WHERE SUBJECT_ID=?', [str(RAW),'93640'])
fields = [d[0] for d in query.description]
notes = [dict(zip(fields,row)) for row in query.fetchall()]
results=[]
for case, pattern, note_ids, date in [
    ('N501',r'Abdominal CT\s+scan this afternoon after receiving blood|CT scan revealed blood peritoneum',{'473836'},None),
    ('N501',r'bleed from \?source, f/u CT',None,'[CLINICAL_LITERAL_REMOVED]'),
    ('N578',r'Renal: low U/O, lasix given to improve diuresis for (?:possible )?extubation',{'470749','470821'},None),
    ('N526',r'HR: 110 \(92 - 110\) bpm',None,'[CLINICAL_LITERAL_REMOVED]')]:
    packet=packets[case]
    c=packet['C_pipeline']['retrieval']['C48']
    scores=packet['C_pipeline']['scores']
    for note in notes:
        if note_ids and note['ROW_ID'] not in note_ids:
            continue
        if date and note['CHARTDATE']!=date:
            continue
        for match in re.finditer(pattern,note['TEXT']):
            hits=[]
            for p in corpus:
                if p['note_id']!=note['ROW_ID'] or p['subject_id']!='93640' or p['start']>=match.end() or p['end_exclusive']<=match.start():
                    continue
                pid=p['passage_id']
                assert note['TEXT'][p['start']:p['end_exclusive']]==p['text']
                def rank(seq):
                    return seq.index(pid)+1 if pid in seq else None
                hits.append({'passage_id':pid,'text':p['text'],'start':p['start'],'end_exclusive':p['end_exclusive'],
                    'ranks':{k:rank([v[0] if isinstance(v,list) else v for v in seq]) for k,seq in packet['C_pipeline']['rankings'].items()},
                    'C_candidate_rank':rank(c['candidate_ids']),
                    'C_rerank_rank':rank(sorted(c['candidate_ids'],key=lambda key:(-scores[key],key))),
                    'saved_score':scores.get(pid),
                    'saved_score_scope':'shared scored union; C rerank rank only assigned when in C candidates',
                    'C_selected_ordinal':rank(c['selected_ids']),
                    'C_skip':[s for s in c['selection_skips'] if s['passage_id']==pid]})
            results.append({'case_id':case,'subject_id':'93640','note_id':note['ROW_ID'],
                'description':note['DESCRIPTION'],'chartdate':note['CHARTDATE'],'charttime':note['CHARTTIME'],
                'start':match.start(),'end_exclusive':match.end(),'quote':match.group(),
                'raw_context':note['TEXT'][max(0,match.start()-140):min(len(note['TEXT']),match.end()+220)],
                'indexed_overlaps':hits})
(OUT/'raw_checks.json').write_text(json.dumps(results,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8')
hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [PACKETS,CORPUS,RAW,Path(__file__)]}
(OUT/'source_hashes.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n',encoding='utf8')
print(json.dumps(results,ensure_ascii=False,indent=2))
