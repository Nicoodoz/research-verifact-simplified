"""Independent literal boundary count using 010 actual references and raw notes."""
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
INPUT = ROOT / 'outputs/010_verifact_baseline_alignment/preparation_001/inputs.jsonl'
REPORTED = ROOT / 'outputs/012_comparative_error_diagnosis/pipeline_001/boundary_candidates.json'
CORPUS = ROOT / 'outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl'
RAW = ROOT / 'data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz'


def main():
    inputs = [json.loads(line) for line in INPUT.read_text(encoding='utf8').splitlines()]
    assert len(inputs) == 650
    subjects = sorted({r['subject_id'] for r in inputs})
    assert subjects == ['15057', '27036', '59250', '59840', '66218', '93640']
    db = duckdb.connect()
    db.execute('CREATE TEMP TABLE selected(subject_id VARCHAR PRIMARY KEY)')
    db.executemany('INSERT INTO selected VALUES (?)', [(sid,) for sid in subjects])
    rows = db.execute('SELECT n.SUBJECT_ID, n.ROW_ID, n.TEXT FROM read_csv_auto(?, all_varchar=true) n JOIN selected s ON n.SUBJECT_ID=s.subject_id', [str(RAW)]).fetchall()
    notes = {(sid, nid): text for sid, nid, text in rows}
    assert len(notes) == len(rows)
    corpus = {(r['subject_id'], r['note_id'], r['start'], r['end_exclusive']): r
              for r in (json.loads(line) for line in CORPUS.read_text(encoding='utf8').splitlines())}
    occurrence = []
    block_count = 0
    for r in inputs:
        reference = r['references']['c48_reference']
        blocks = re.split(r'(?m)(?=^\d+\. Date:)', reference)[1:]
        for block in blocks:
            header = re.match(r'(\d+)\. Date:.*?Note ID: (\d+), Raw characters: \[(\d+),(\d+)\) \| Text: ', block)
            assert header, r['case_id']
            ordinal, note_id, start, end = header.groups()
            start, end = int(start), int(end)
            text = notes[r['subject_id'], note_id]
            # Actual whole substring, excluding the one inter-block delimiter newline.
            expected = text[start:end]
            actual = block[header.end():]
            assert actual == expected or actual == expected + '\n'
            passage = corpus[r['subject_id'], note_id, start, end]
            assert passage['text'] == expected
            block_count += 1
            m = re.search(r'\b(No|not|without|denies)\s*$', text[:start], re.I)
            if not m:
                continue
            occurrence.append({'case_id': r['case_id'], 'proposition_id': r['proposition_id'],
                'subject_id': r['subject_id'], 'note_id': note_id, 'passage_id': passage['passage_id'],
                'selected_ordinal': int(ordinal), 'start': start, 'end_exclusive': end,
                'preceding_token': m.group(1), 'token_start': m.start(),
                'boundary_context': text[max(0, m.start()-40):min(len(text),start+80)]})
    reported = json.loads(REPORTED.read_text(encoding='utf8'))
    expected_keys = set()
    for item in reported:
        trace = item['trace']
        for passage in trace['passages']:
            if passage['selected_ordinal'] is not None and passage['start'] > trace['start']:
                expected_keys.add((item['case_id'], trace['note_id'], passage['start']))
    actual_keys = {(r['case_id'], r['note_id'], r['start']) for r in occurrence}
    assert len(occurrence) == len(actual_keys)
    assert actual_keys == expected_keys, {'missing': sorted(expected_keys-actual_keys), 'extra': sorted(actual_keys-expected_keys)}
    cuts = Counter((r['subject_id'],r['note_id'],r['start']) for r in occurrence)
    result = {'claims_checked': 650, 'actual_selected_blocks_checked': block_count,
              'literal_occurrences': len(occurrence), 'distinct_claims': len({r['case_id'] for r in occurrence}),
              'distinct_raw_cutpoints': len(cuts), 'raw_cutpoint_definition': '(subject_id, note_id, start character)',
              'candidate_sets_match_012': True,
              'rule': r'case-insensitive whole word No|not|without|denies followed only by whitespace immediately before actual selected start',
              'not_clinical_error_count': True, 'not_causal_attribution_rate': True,
              'zero_api_calls': True,
              'cutpoints': [{'subject_id': k[0], 'note_id': k[1], 'start': k[2], 'occurrences': v} for k,v in sorted(cuts.items())]}
    for name, value in [('result.json',result), ('occurrences.json',occurrence)]:
        (OUT/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf8')
    paths = [INPUT,REPORTED,CORPUS,RAW,Path(__file__)]
    hashes = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (OUT/'source_hashes.json').write_text(json.dumps(hashes,sort_keys=True,indent=2)+'\n',encoding='utf8')
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__ == '__main__':
    main()
