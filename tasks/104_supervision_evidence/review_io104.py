"""View only frozen blinded training cases; never joins GT or teachers."""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/104_supervision_evidence'

def cases():
    return [json.loads(s) for s in (PRIVATE / 'blind_cases.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]

def compact_full(reference, dense=False):
    """Lossless review view: repeated metadata dictionary; every text character kept."""
    pattern = re.compile(r'(?m)^(\d+)\. Date: ([^,\n]+), Time: ([^,\n]+), Note Category: ([^,\n]+), Note Description: ([^\n]+?) \| Text: ')
    hits = list(pattern.finditer(reference))
    assert hits
    meta = {}
    pieces = []
    rebuilt = reference[:hits[0].start()]
    for i, hit in enumerate(hits):
        key = hit.group(2, 3, 4, 5)
        meta.setdefault(key, len(meta) + 1)
        end = hits[i+1].start() if i+1 < len(hits) else len(reference)
        body = reference[hit.end():end]
        shown = ' '.join(body.split()) if dense else body
        assert ''.join(shown.split()) == ''.join(body.split())
        pieces.append((f'[{hit.group(1)} M{meta[key]} @{hit.end()}:{end}] ' + shown + '\n') if dense else (f'[unit {hit.group(1)}; M{meta[key]}; original text offset {hit.end()}:{end}]\n' + shown))
        rebuilt += hit.group() + body
    assert rebuilt == reference
    legend = '\n'.join(f'M{v}: date={k[0]} time={k[1]} category={k[2]} description={k[3]}' for k, v in meta.items())
    return reference[:hits[0].start()] + '\nMETADATA DICTIONARY (lossless):\n' + legend + '\nALL ORIGINAL UNIT TEXTS (unfiltered):\n' + ''.join(pieces)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('indexes', type=int, nargs='+')
    p.add_argument('--outline', action='store_true')
    p.add_argument('--compact-full', action='store_true')
    p.add_argument('--dense-full', action='store_true', help='All reference text; display-only whitespace folding within units')
    a = p.parse_args()
    rows = {r['review_index']: r for r in cases()}
    for idx in a.indexes:
        r = rows[idx]
        assert hashlib.sha256(r['reference'].encode()).hexdigest() == r['reference_sha256']
        print(f"\n=== BLIND CASE {idx}; ID {r['id']}; SHA {r['reference_sha256']}; chars={len(r['reference'])} ===")
        print('CLAIM:', r['claim'])
        if not a.outline:
            print('FULL REFERENCE (exact Python character offsets, no truncation; dense view folds only whitespace):\n' + (compact_full(r['reference'], dense=a.dense_full) if a.compact_full or a.dense_full else r['reference']))
            print(f'=== END FULL REFERENCE {idx}; chars={len(r["reference"])} ===')

if __name__ == '__main__':
    main()
