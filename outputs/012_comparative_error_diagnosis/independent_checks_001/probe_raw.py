import json
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
packets = [json.loads(x) for x in (ROOT / 'outputs/012_comparative_error_diagnosis/materials_001/packets.jsonl').read_text(encoding='utf8').splitlines()]
packets = {r['row']['case_id']: r for r in packets}
corpus = [json.loads(x) for x in (ROOT / 'outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl').read_text(encoding='utf8').splitlines()]
db = duckdb.connect()
raw = ROOT / 'data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz'
con = db.execute('SELECT * FROM read_csv_auto(?, all_varchar=true) WHERE SUBJECT_ID IN (?,?)', [str(raw), '15057', '66218'])
fields = [d[0] for d in con.description]
notes = [dict(zip(fields, row)) for row in con.fetchall()]
results = []
for case, pattern in [('N086', r'No\s+nausea'), ('N395', r'F/u Ortho re: fx|Consults: General surgery, Neuro surgery, Ortho, Plastics')]:
    r = packets[case]
    retr = r['C_pipeline']['retrieval']['C48']
    for note in notes:
        if note['SUBJECT_ID'] != r['row']['subject_id']:
            continue
        if case == 'N086' and note['ROW_ID'] != '375697':
            continue
        for match in re.finditer(pattern, note['TEXT'], re.I):
            overlapping = [p for p in corpus if p['note_id'] == note['ROW_ID'] and p['start'] < match.end() and p['end_exclusive'] > match.start()]
            passages = []
            for p in overlapping:
                pid = p['passage_id']
                def position(values):
                    return values.index(pid) + 1 if pid in values else None
                passages.append({'passage_id': pid, 'start': p['start'], 'end_exclusive': p['end_exclusive'], 'text': p['text'],
                    'rankings': {k: position([v[0] if isinstance(v, list) else v for v in ranked]) for k, ranked in r['C_pipeline']['rankings'].items()},
                    'candidate_position': position(retr['candidate_ids']),
                    'rerank_position': position(sorted(retr['candidate_ids'], key=lambda key: (-r['C_pipeline']['scores'][key], key))), 'score': r['C_pipeline']['scores'].get(pid),
                    'selected': pid in retr['selected_ids'], 'selection_skips': [s for s in retr['selection_skips'] if pid in str(s)]})
            results.append({'case_id': case, 'note_id': note['ROW_ID'], 'subject_id': note['SUBJECT_ID'],
                'chartdate': note['CHARTDATE'], 'charttime': note['CHARTTIME'], 'description': note['DESCRIPTION'],
                'raw_span': [match.start(), match.end()], 'raw_quote': match.group(),
                'raw_context': note['TEXT'][max(0,match.start()-200):match.end()+400], 'overlapping_passages': passages})
(OUT / 'raw_probes.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print(json.dumps(results, ensure_ascii=False, indent=2))
