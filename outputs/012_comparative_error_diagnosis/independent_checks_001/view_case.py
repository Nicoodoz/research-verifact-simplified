import json
import sys
import re
from pathlib import Path

root = Path(__file__).resolve().parents[3]
rows = [json.loads(x) for x in (root / 'outputs/012_comparative_error_diagnosis/materials_001/packets.jsonl').read_text(encoding='utf8').splitlines()]
r = next(x for x in rows if x['row']['case_id'] == sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else 'outputs'
if mode == 'outputs':
    print(json.dumps(r['row'], ensure_ascii=False))
    print('PARENT', r['proposition']['parent_text_chunk'])
    print('ORIGINAL FULL', json.dumps(r['original'], ensure_ascii=False))
    for arm, output in r['current_outputs'].items():
        print(arm, output['output_text'])
elif mode in r['input']['references']:
    print(r['input']['references'][mode])
elif mode == 'pipeline':
    print(json.dumps(r['C_pipeline'], ensure_ascii=False, indent=2))
elif mode == 'scope':
    print(json.dumps(r['raw_scope_notes'], ensure_ascii=False, indent=2))
elif mode == 'evidence':
    patterns = {'N086': r'nausea|N/V', 'N095': r'kcl|potassium|K\+',
                'N139': r'baseline|stable|BP |blood pressure|hypotens',
                'N182': r'educat|teach|coping|anxi|support',
                'N188': r'angiog|dissection|cath|CTA|stent',
                'N388': r'pulm|focus|PULM|cardiac|bleed|pain',
                'N395': r'ortho|consult'}
    for arm, text in r['input']['references'].items():
        print('ARM', arm)
        blocks = re.split(r'(?m)(?=^\d+\. Date:)', text)
        for block in blocks[1:]:
            if re.search(patterns[sys.argv[1]], block, re.I):
                print(block)
    print('HUMAN', json.dumps(r['human'], ensure_ascii=False))
