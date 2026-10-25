from pathlib import Path
import json,hashlib
R=Path('D:/Research-VeriFact');O=R/'outputs/013_multi_mechanism_screen';T=Path(__file__).resolve().parent
def jl(p):return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x]
items={r['case_id']:r for r in jl(O/'screen_inputs_001/inputs.jsonl')}
corpus={p['passage_id']:p for p in jl(R/'outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl')}
checks=json.loads((O/'membership_backcheck_001/checks.json').read_text(encoding='utf-8'))
for c in checks:
    item=items[c['case_id']];p=corpus[c['passage_id']]
    assert p['subject_id']==item['subject_id'] and p['note_id']==c['note_id'] and p['text']==c['raw_text']
    for arm,expected in c['membership'].items():assert (c['passage_id'] in item['retrieval'][arm]['selected_ids'])==expected
for cid in ('N305','N425','N644'):
    own=[c for c in checks if c['case_id']==cid]
    assert own and all(all(c['membership'].values()) for c in own)
# Read only the saved final references to show what the selector removed.
for cid in ('N501',):
    print(cid)
    for arm in ('baseline','selector'):
        item=items[cid];print(arm)
        for k in item['retrieval'][arm]['selected_ids']:
            p=corpus[k]
            if 'CT' in p['text']:print(p['note_id'],p['start'],p['text'])
e={'independent_membership_assertions':len(checks),'corrections_confirmed':['N305','N425','N644'],'note_patient_text_and_final_selection_checked':True}
(T/'membership_checks.json').write_text(json.dumps(e,indent=2)+'\n',encoding='utf-8');print(json.dumps(e))
