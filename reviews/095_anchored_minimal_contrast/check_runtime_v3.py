"""Read-only independent regression for fixes identified by this reviewer."""
import sys,ast,json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[2];T=R/'tasks/095_anchored_minimal_contrast';O=R/'outputs/095_anchored_minimal_contrast';sys.path.insert(0,str(T))
import pricing095_v3 as p
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
fr=read(O/'runtime_v3_freeze.json')
for path,hh in fr['sources'].items():assert sha(R/path)==hh
old=read(O/'pricing_v2_freeze.json')
assert sha(T/'workflow095_pre_resume_fix.py')==old['sources']['tasks/095_anchored_minimal_contrast/workflow095.py']
j={'bound_cny':1};tr={'http_status':200,'started_utc':'2026-09-27T23:01:00+08:00','ended_utc':'2026-09-27T23:02:00+08:00','body_text':json.dumps({'model':'deepseek-v4-flash-0731','usage':{'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':{'cached_tokens':200}}})}
assert abs(p.charge(j,tr)-.00168)<1e-12
for status in [0,408,429,500,502,503,504]:assert p.charge(j,dict(tr,http_status=status))==1
assert p.charge(j,dict(tr,outcome_unknown=True))==1
assert p.charge(j,None)==1
assert p.charge(j,dict(tr,body_text='not JSON'))==1
# Extract only pure helper AST: do not import the paid runner or instantiate its DB.
tree=ast.parse((T/'run095_v3.py').read_text());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='remaining_baseline')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'audited-pure-function','exec'),ns)
jobs=[{'id':'A','body_sha256':'x'},{'id':'B','body_sha256':'y'},{'id':'C','body_sha256':'z'},{'id':'D','body_sha256':'d'}]
success={'methodB':{'job':{'id':'A','body_sha256':'x','arm':'B','phase':'method'}},'wrongbody':{'job':{'id':'B','body_sha256':'different','arm':'B','phase':'method'}},'wrongarm':{'job':{'id':'C','body_sha256':'z','arm':'C','phase':'method'}},'invalid_core_B':{'job':{'id':'D','body_sha256':'d','arm':'B','phase':'baseline'},'core_valid':False}}
assert ns['remaining_baseline'](jobs,success)==jobs[1:3]
out={'status':'PASS targeted runtime-v3 regression','non200_and_unknown_preserve_bound':True,'cross_phase_same_ID_body_B_filtered':True,'different_body_and_arm_preserved':True,'invalid_HTTP200_not_repeated':True,'original_order_preserved':True,'old_workflow_snapshot_exact':True,'runtime_freeze_sha256':sha(O/'runtime_v3_freeze.json')}
with (Path(__file__).parent/'runtime_v3_checks.json').open('x',encoding='utf-8') as f:json.dump(out,f,ensure_ascii=False,indent=2)
print(out)
