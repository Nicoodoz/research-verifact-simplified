"""Prepare paired100 without GT or result-based selection; no model call."""
from pathlib import Path
import json,hashlib,re
R=Path(__file__).resolve().parents[2];P=R/'.local_models/158_minimal_reason'
FOLLOWUP='''The verdict in the preceding assistant message is fixed. Do not reclassify it or change it. Give one sentence of at most 35 words stating the minimum decisive reference evidence for that verdict. Supported means the assertion is fully supported. Not Supported means it is addressed but contradicted or only partly supported. Not Addressed means the specific assertion is not addressed; it does not mean the patient lacks that fact. Do not confuse partial support with not addressed. Omit unnecessary details and dates. Only when a date is essential to explaining a temporal assertion, copy its exact original representation from the reference, including deidentified years and brackets; never convert, normalize, infer or replace a year. Do not invent facts, quotations, or causal or temporal connections. Explain the evidence direction rather than repeating a label or adding a conclusion to an opposite explanation. If no honest short explanation in the fixed direction can be given, return status "unable" and reason null. Return only JSON: {"status":"explained","reason":"brief reason"} or {"status":"unable","reason":null}.'''

def main():
    if (P/'inputs.jsonl').exists():raise FileExistsError('Preserve158 preparation')
    source=[json.loads(s) for s in (R/'.local_models/151_fixed_reason_transfer/inputs.jsonl').read_text(encoding='utf-8').splitlines()]
    selected=[]
    for label,n in [('Supported',60),('Not Supported',14),('Not Addressed',26)]:
        group=sorted([r for r in source if r['fixed_verdict']==label],key=lambda r:hashlib.sha256(('minimal_reason|'+r['id']).encode()).hexdigest())[:n]
        assert len(group)==n;selected+=group
    assert len(selected)==100 and all(set(r)=={'id','claim','reference','fixed_verdict'} for r in selected)
    P.mkdir(parents=True,exist_ok=True);(P/'inputs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected),encoding='utf-8')
    (P/'selection.json').write_text(json.dumps(dict(N=100,ids=[r['id'] for r in selected],GT_used=False,previous_reason_status_used=False,rule='predicted-label strata and SHA256(minimal_reason|ID)'),indent=2)+'\n',encoding='utf-8')
    worker=(R/'tasks/147_fixed_reason/worker147.py').read_text(encoding='utf-8')
    worker=re.sub(r"FOLLOWUP='''.*?'''",'FOLLOWUP='+repr(FOLLOWUP),worker,flags=re.S)
    worker=worker.replace('started+3600','started+900').replace("for arm in ('reason120','reason_base9b'):","for arm in ('reason_base9b',):").replace("N=60,arms=['reason120','reason_base9b']","N=100,arms=['reason_base9b']").replace('total=120','total=100')
    (R/'tasks/158_minimal_reason/worker158.py').write_text(worker,encoding='utf-8')
    print(json.dumps(dict(N=100,GT_used=False,paid_calls=0)))

if __name__=='__main__':main()
