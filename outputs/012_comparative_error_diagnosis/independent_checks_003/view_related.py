import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
packet_file = ROOT/'outputs/012_comparative_error_diagnosis/materials_001/packets.jsonl'
rows = [json.loads(line) for line in packet_file.read_text(encoding='utf8').splitlines()]
r = next(row for row in rows if row['row']['case_id'] == sys.argv[1])
patterns = {'N501': r'f/u CT|Abdominal CT|CT scan|if.*unstable|unstable.*CT',
            'N526': r'tachy|HR:|Heart Rate|heart rate|\bHR\b',
            'N578': r'low U/O|low UOP|marginal uop|extubation|UOP decreasing|for diuresis'}
for arm, text in r['input']['references'].items():
    for block in re.split(r'(?m)(?=^\d+\. Date:)', text)[1:]:
        if (sys.argv[1] == 'N526' and arm == 'c48_reference') or re.search(patterns[sys.argv[1]], block, re.I):
            print(arm, block)
print('HUMAN', json.dumps(r['human'], ensure_ascii=False))
