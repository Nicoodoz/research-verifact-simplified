"""Fixed class-balanced patient-rotation sampling; no prediction/review filtering.

The command writes clinical rows only under the existing private .local_models
tree. The function is independently reusable and never alters a source row.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
LABELS = ('Supported', 'Not Supported', 'Not Addressed')


def patient_rotation_sample(pool, quota=243, seed=117027):
    if len(pool) != len({r['id'] for r in pool}) or any(r['GT'] not in LABELS for r in pool):
        raise ValueError('Unique IDs with unchanged original three-class GT are required')
    rng = random.Random(seed)

    def rotation(rows, count):
        groups = {}
        for row in sorted(rows, key=lambda r: r['id']):
            groups.setdefault(str(row['sid']), []).append(row)
        patients = sorted(groups)
        rng.shuffle(patients)
        for patient in patients:
            rng.shuffle(groups[patient])
        chosen = []
        while len(chosen) < count:
            moved = False
            for patient in patients:
                if groups[patient]:
                    chosen.append(groups[patient].pop())
                    moved = True
                    if len(chosen) == count:
                        break
            if not moved:
                raise ValueError('Insufficient real examples for fixed class quota')
        return chosen

    selected = []
    for label in LABELS:
        selected += rotation([r for r in pool if r['GT'] == label], quota)
    return rotation(selected, len(LABELS)*quota)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to((ROOT/'.local_models').resolve()):
        parser.error('Clinical training rows must stay in .local_models')
    pool = [json.loads(line) for line in args.input.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    if len(pool) != 2945 or len({str(r['sid']) for r in pool}) != 32:
        raise ValueError('122 uses the frozen original32-patient2945 pool')
    chosen = patient_rotation_sample(pool)
    body = ''.join(json.dumps(r, ensure_ascii=False, separators=(',', ':'))+'\n' for r in chosen).encode('utf-8')
    if args.output.exists() and args.output.read_bytes() != body:
        raise FileExistsError('Preserve existing different training selection')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(body)
    print(json.dumps(dict(N=len(chosen), patients=len({str(r['sid']) for r in chosen}),
                          GT=dict(Counter(r['GT'] for r in chosen)), seed=117027,
                          clinical_rows_written_to_private_path=True), ensure_ascii=False))


if __name__ == '__main__':
    main()
