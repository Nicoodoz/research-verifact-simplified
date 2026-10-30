"""CPU source lookup for a small, already frozen diagnostic case list.

This locates existing reference fragments; it neither generates evidence nor
assigns a new label. Full clinical material must stay in a private directory.
"""
from pathlib import Path
import argparse
import csv
import gzip
import json
import re

ROOT = Path(__file__).resolve().parents[2]
HEAD = re.compile(r'(?m)^(\d+)\. Date: (.*?), Time: (.*?), Note Category: (.*?), Note Description: (.*?) \| Text: ')


def rows(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8-sig').splitlines() if s.strip()]


def fragments(case):
    matches = list(HEAD.finditer(case['reference']))
    for j, match in enumerate(matches):
        end = matches[j + 1].start() if j + 1 < len(matches) else len(case['reference'])
        number, day, tm, category, description = match.groups()
        yield dict(id=case['id'], sid=str(case['sid']), unit=int(number), date=day,
                   time=tm, category=category, description=description,
                   source_text=case['reference'][match.end():end].strip())


def match_fragment(fragment, notes):
    # Author headers use CHARTDATE and the time portion of CHARTTIME. These
    # can refer to different dates in the source; do not silently repair them.
    candidates = [n for n in notes if n['CHARTDATE'][:10] == fragment['date']
                  and n['CATEGORY'].strip() == fragment['category']
                  and n['DESCRIPTION'].strip() == fragment['description']
                  and (n['CHARTTIME'][11:19] if n['CHARTTIME'] else 'Unknown') == fragment['time']]
    normal = lambda text: re.sub(r'\s+', ' ', text).strip()
    found = [n['ROW_ID'] for n in candidates
             if normal(fragment['source_text']) in normal(n['TEXT'])]
    return dict(fragment, metadata_candidates=[n['ROW_ID'] for n in candidates],
                exact_whitespace_normalized_matches=found)


def run(cases_path, source, out):
    out = out.resolve()
    if not out.is_relative_to((ROOT / '.local_models').resolve()):
        raise ValueError('Clinical source lookup output must remain private')
    cases = rows(cases_path)
    ranges = {str(r['sid']): re.findall(r'Hospital Admission (?:Start|End): ([0-9-]+)', r['reference']) for r in cases}
    if len({r['id'] for r in cases}) != len(cases) or not all(len(v) == 2 for v in ranges.values()):
        raise ValueError('Require distinct IDs and explicit original admission windows')
    notes = {sid: [] for sid in ranges}
    excluded = 0
    csv.field_size_limit(2**31 - 1)
    with gzip.open(source, 'rt', encoding='utf-8', newline='') as stream:
        for note in csv.DictReader(stream):
            sid = note['SUBJECT_ID']
            if sid not in ranges:
                continue
            lo, hi = ranges[sid]
            if not lo <= note['CHARTDATE'][:10] <= hi:
                continue
            if note['CATEGORY'].strip().lower() == 'discharge summary':
                excluded += 1
                continue
            notes[sid].append(note)
    out.mkdir(parents=True, exist_ok=True)
    for sid, values in notes.items():
        (out / ('notes_' + sid + '.jsonl')).write_text(
            ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in values), encoding='utf-8')
    links = [match_fragment(f, notes[str(case['sid'])]) for case in cases for f in fragments(case)]
    (out / 'source_links.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in links), encoding='utf-8')
    summary = dict(cases=len(cases), patients=len(notes), eligible_notes=sum(map(len, notes.values())),
                   discharge_summaries_excluded=excluded, matched_units=sum(bool(r['exact_whitespace_normalized_matches']) for r in links),
                   total_units=len(links), ambiguous_units=sum(len(r['exact_whitespace_normalized_matches']) > 1 for r in links),
                   note_matching_only=True, not_a_classifier_result=True, GT_unchanged=True)
    (out / 'source_summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cases', type=Path, required=True)
    parser.add_argument('--source', type=Path, default=ROOT / 'data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.cases, args.source, args.out)))
