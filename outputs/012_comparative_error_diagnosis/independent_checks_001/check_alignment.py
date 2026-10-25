"""Independent, read-only reconstruction. Does not import task 012 code."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
P10 = ROOT / 'outputs/010_verifact_baseline_alignment'
P12 = ROOT / 'outputs/012_comparative_error_diagnosis/alignment_002'
RAW = ROOT / 'data/00_raw/verifact-bhc/1.1.0'
USED = set()


def mark(path):
    path = Path(path)
    USED.add(path)
    return path


def jl(path):
    return [json.loads(line) for line in mark(path).read_text(encoding='utf8').splitlines()]


def js(path):
    return json.loads(mark(path).read_text(encoding='utf8'))


def cs(path):
    with mark(path).open(encoding='utf8', newline='') as f:
        return list(csv.DictReader(f))


def keyed(rows, key):
    result = {row[key]: row for row in rows}
    assert len(result) == len(rows), ('duplicate', key)
    return result


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def verdict_objects(text):
    decoder = json.JSONDecoder()
    found = []
    for pos, char in enumerate(text):
        if char != '{':
            continue
        try:
            value, end = decoder.raw_decode(text[pos:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get('verdict') in {'Supported', 'Not Supported', 'Not Addressed'}:
            found.append((pos, pos + end, value['verdict']))
    return found


def direction(a, b):
    return {(True, True): 'both_correct', (False, False): 'both_wrong',
            (True, False): 'old_correct_new_wrong', (False, True): 'old_wrong_new_correct'}[(a, b)]


def main():
    cohort = keyed(cs(P10 / 'preparation_001/cohort.csv'), 'proposition_id')
    assert len(cohort) == 650
    assert mark(P12 / 'cohort.csv').read_bytes() == mark(P10 / 'preparation_001/cohort.csv').read_bytes()
    inputs = keyed(jl(P10 / 'preparation_001/inputs.jsonl'), 'proposition_id')
    aligned = jl(P12 / 'aligned_materials.jsonl')
    aligned = keyed([dict(item, pid=item['input']['proposition_id']) for item in aligned], 'pid')
    ledger = keyed(jl(P12 / 'ledger.jsonl'), 'proposition_id')
    for rows in (inputs, aligned, ledger):
        assert set(rows) == set(cohort)
    db = duckdb.connect()
    db.execute('CREATE TEMP TABLE selected(proposition_id VARCHAR PRIMARY KEY)')
    db.executemany('INSERT INTO selected VALUES (?)', [(pid,) for pid in cohort])
    vpath = mark(RAW / 'verifact/verdicts.parquet')
    query = db.execute('SELECT v.* FROM read_parquet(?) v JOIN selected s USING(proposition_id) WHERE model=? AND rater_alias=?',
                       [str(vpath), 'R1-70B', 'v1.1.0-rater-121'])
    columns = [col[0] for col in query.description]
    original = keyed([dict(zip(columns, row)) for row in query.fetchall()], 'proposition_id')
    assert set(original) == set(cohort)
    rpath = mark(RAW / 'verifact/reference_payloads.parquet')
    refs = dict(db.execute('SELECT DISTINCT r.reference_id, r.reference FROM read_parquet(?) r JOIN read_parquet(?) v USING(reference_id) JOIN selected s USING(proposition_id) WHERE v.model=? AND v.rater_alias=?',
                           [str(rpath), str(vpath), 'R1-70B', 'v1.1.0-rater-121']).fetchall())
    config = [row for row in cs(RAW / 'verifact/rater_configurations.csv') if row['rater_alias'] == 'v1.1.0-rater-121']
    assert len(config) == 1
    normalized = keyed(jl(P10 / 'analysis_001/normalized_responses.jsonl'), 'request_id')
    jobs = keyed(jl(P10 / 'preparation_001/jobs.jsonl'), 'request_id')
    assignments = cs(P10 / 'preparation_001/assignments.csv')
    assignments = {(r['proposition_id'], r['arm']): r for r in assignments}
    assert len(assignments) == 1300
    received = {}
    for path in sorted((P10 / 'live/judge').glob('receipt_*.json')):
        receipt = js(path)
        if receipt['transport']['http_status'] == 200:
            assert receipt['request_id'] not in received
            received[receipt['request_id']] = json.loads(receipt['transport']['body_text'])
    authors = {}
    final_checks = []
    for pid, source in inputs.items():
        current = aligned[pid]
        row = ledger[pid]
        assert current['row'] == row
        assert current['input'] == source
        assert current['original'] == original[pid]
        assert original[pid]['reference_id'] == source['reference_id']
        reference = refs[source['reference_id']]
        assert reference == source['references']['verifact_reference']
        assert hashlib.sha256(reference.encode()).hexdigest() == source['reference_id']
        assert row['O'] == original[pid]['verdict']
        objects = verdict_objects(original[pid]['reasoning_final_answer'])
        assert objects and {o[2] for o in objects} == {row['O']}
        final_checks.append({'proposition_id': pid, 'case_id': source['case_id'], 'object_spans': objects, 'published_verdict': row['O']})
        for key, arm in [('V', 'verifact_reference'), ('C', 'c48_reference')]:
            assignment = assignments[pid, arm]
            rid = assignment['request_id']
            body = jobs[rid]['body']
            response = normalized[rid]
            assert hashlib.sha256(canonical(body)).hexdigest() == assignment['body_sha256']
            assert current['current_bodies'][arm] == body
            assert current['current_outputs'][arm] == response
            user = json.loads(body['messages'][-1]['content'])
            assert user['proposition'] == source['text']
            assert user['reference'] == source['references'][arm]
            raw_text = received[rid]['choices'][0]['message']['content']
            assert raw_text == response['output_text']
            parsed = json.loads(raw_text)
            assert parsed['verdict'] == response['verdict'] == row[key]
            assert response['proposition_id'] == pid
        gt = cohort[pid]['human_gt']
        assert row['human_gt'] == gt
        assert row['author_type'] == cohort[pid]['author_type']
        pattern = ''.join('1' if row[k] == gt else '0' for k in 'OVC')
        assert pattern == row['correctness_pattern']
        assert row['error_union'] == (pattern != '111')
        author = authors.setdefault(row['author_type'], {k: Counter() for k in ['O_to_V', 'V_to_C', 'O_to_C', 'correctness_pattern']})
        author['correctness_pattern'][pattern] += 1
        for pair in ['O_to_V', 'V_to_C', 'O_to_C']:
            a, b = pair.split('_to_')
            label = direction(row[a] == gt, row[b] == gt)
            assert label == row[pair]
            author[pair][label] += 1
    summary = js(P12 / 'summary.json')
    union = sum(row['correctness_pattern'] != '111' for row in ledger.values())
    assert union == summary['error_union'] == 195
    assert 650 - union == summary['all_three_correct'] == 455
    assert authors == summary['authors']
    assert summary['original_final_output_checks'] == {'matches': 650}
    result = {'scope': 'Independent machine verification; not a full independent audit or clinical adjudication',
              'claims': 650, 'error_union': union, 'all_three_correct': 650 - union,
              'authors': authors, 'original_final_verdict_matches': len(final_checks),
              'canonical_010_bodies_and_received_outputs_rebound': 1300,
              'rater_configuration': config, 'findings': [], 'zero_api_calls': True}
    (OUT / 'machine_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf8')
    (OUT / 'original_final_checks.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in final_checks), encoding='utf8')
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(USED)}
    (OUT / 'source_hashes.json').write_text(json.dumps(hashes, indent=2, sort_keys=True) + '\n', encoding='utf8')
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
