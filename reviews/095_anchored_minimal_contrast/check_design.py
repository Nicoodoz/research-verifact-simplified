"""Independent zero-API frozen design checks and synthetic input-isolation checks."""
import sys,json,hashlib,copy,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2];T=R/'tasks/095_anchored_minimal_contrast';O=R/'outputs/095_anchored_minimal_contrast';P=R/'.local_models/095'
sys.path.insert(0,str(T))
import method095 as m
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=read(O/'experiment_freeze.json')
for path,hh in freeze['sources'].items():assert sha(R/path)==hh
sample=rows(O/'screen_sample.jsonl'); ext=rows(O/'extension_registered_order.jsonl'); discovery=rows(O/'diagnosis_sample.jsonl')
assert len(sample)==300 and len({r['id'] for r in sample})==300
assert len(ext)==600 and len({r['id'] for r in ext})==600
assert not ({r['id'] for r in sample}&{r['id'] for r in ext})
assert not (({r['id'] for r in sample}|{r['id'] for r in ext})&{r['id'] for r in discovery})
assert collections.Counter(r['panel'] for r in sample)=={'natural':200,'mechanism':100}
assert collections.Counter(r['GT'] for r in sample if r['panel']=='mechanism')=={'Supported':34,'Not Supported':33,'Not Addressed':33}
inp={r['id']:r for r in rows(P/'screen_inputs.jsonl')}
for j in rows(P/'construct_jobs.jsonl'):
    b=j['body']; u=json.loads(b['messages'][1]['content']);x=inp[j['id']]
    assert u=={'claim':x['text'],'reference':x['reference']}
    assert b['enable_thinking'] is False and b['model']=='deepseek-v4-flash-0731'
    assert j['phase']=='method'
ref='1. Date: [CLINICAL_LITERAL_REMOVED], Time: 12:00:00, Note Category: Synthetic, Note ID: synthetic, Raw characters: [0,32) | Text: Dose was increased to 20 mg daily.'
r={'text':'Dose was increased to 10 mg daily.','reference':ref}
v=m.validate({'applicable':True,'attribute':'number','old_span':'10','new_span':'20','source_value':'20','anchors':[{'reference_id':1,'quote':'Dose was increased to 20 mg daily.'}]},r)
assert v['valid'] and v['alternative']=='Dose was increased to 20 mg daily.'
assert r['reference'][v['anchors'][0]['reference_start']:v['anchors'][0]['reference_end']]==v['anchors'][0]['quote']
bad={'applicable':True,'attribute':'number','old_span':'10','new_span':'30','source_value':'30','anchors':[{'reference_id':1,'quote':'Dose was increased to 20 mg daily.'}]}
assert not m.validate(bad,r)['valid']
assert not m.validate({'applicable':False},r)['valid']
t=read(P/'judge_template.json');e=m.judge(t,r,'E',v);c=m.judge(t,r,'C',v);b=m.judge(t,r)
assert e['messages'][0]==c['messages'][0]
eu=json.loads(e['messages'][1]['content']);cu=json.loads(c['messages'][1]['content'])
assert eu=={k:v for k,v in cu.items() if k!='alternative_hypothesis'}
assert eu['proposition']==r['text'] and eu['reference']==r['reference']
assert set(json.loads(b['messages'][1]['content']))=={'proposition','reference'}
for body in [m.builder(r),m.checker(r,v),e,c,b]:
    assert not (set(json.loads(body['messages'][1]['content']))&{'GT','label','B_G','B_raw','original'})
out={'status':'PASS scoped structural design checks','N':300,'extension_N':600,'GT_input_whitelist_verified':True,'E_C_only_alternative_difference_verified':True,'synthetic_source_validation_verified':True,'source_freeze':{str(p.relative_to(R)):sha(p) for p in [T/'workflow095.py',T/'decision_clarification.md',T/'method095.py']}}
with (Path(__file__).parent/'design_checks.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(out)
