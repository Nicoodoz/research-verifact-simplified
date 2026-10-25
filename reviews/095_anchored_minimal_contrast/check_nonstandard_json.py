import json,re
from pathlib import Path
R=Path(__file__).resolve().parents[2];D=Path(__file__).parent
rr=[json.loads(x) for x in (R/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl').read_text().splitlines()]
ids=set(json.loads((D/'final_checks.json').read_text())['nonstandard_JSON_IDs']);out=[]
for r in rr:
    if r['id'] not in ids:continue
    z=json.loads((R/r['B']['receipt_path']).read_text());n=json.loads(z.get('transport',z)['body_text']);t=n['choices'][0]['message'].get('content') or ''
    found=re.findall(r'"verdict"\s*:\s*"(Supported|Not Supported|Not Addressed)"',t)
    if r['B_raw_valid']:assert found==[r['predictions']['B_raw']]
    elif found:assert 'unfinished_core_field' in r['B']['parsed']['parser_errors']
    assert not r['B_core_valid'] and r['predictions']['B_PriorG'] is None
    out.append({'id':r['id'],'content_chars':len(t),'raw_valid':r['B_raw_valid'],'valid_verdict_fields':len(found),'frozen_parser_rejects_partial_core_despite_literal_verdict':bool(found) and not r['B_raw_valid'],'final_imputed':False})
with (D/'nonstandard_json_checks.json').open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print('verified',len(out),'nonstandard JSON records, no final imputation')
