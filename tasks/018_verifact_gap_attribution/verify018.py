"""Offline reconstruction and audit handoff; no requests or source mutations."""
from pathlib import Path
from collections import Counter
import argparse,subprocess,socket
import common018 as c
from analyze018 import analyze
from diagnose018 import load_notes,build as diagnose
from trace018 import build as trace

NAV={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','reviews/README.md','.gitattributes'}

def validate_rows(rows,cohort):
    expected={r['proposition_id']:r for r in cohort}
    c.require(len(expected)==len(cohort),'Duplicate cohort')
    c.require(len(rows)==len(expected) and len({r['proposition_id'] for r in rows})==len(rows),'Duplicate/missing ledger')
    c.require({r['proposition_id'] for r in rows}==set(expected),'Cohort mismatch')
    for r in rows:
        g=expected[r['proposition_id']]
        for key in ('human_gt','subject_id','author_type','proposition_type','invalid'):
            c.require(r[key]==g[key],'Frozen cohort field differs: '+key)
        systems=('O','V','C') if r['cohort']=='010' else ('O','C','Q')
        c.require(all(r[s] in c.LABELS for s in systems),'Illegal label')
        c.require(r['bucket']==c.bucket(r['O'],r['C'],r['human_gt']),'Wrong correctness bucket')

def equal_contents(original,replay):
    files=[p for p in original.rglob('*') if p.is_file() and p.name!='manifest.json']
    c.require({p.relative_to(original).as_posix() for p in files}=={p.relative_to(replay).as_posix() for p in replay.rglob('*') if p.is_file() and p.name!='manifest.json'},'Replay inventory')
    for p in files:c.require(p.read_bytes()==(replay/p.relative_to(original)).read_bytes(),'Replay differs: '+str(p))
    return len(files)

def verify(out):
    c.require(not out.exists(),'Verification exists')
    def blocked(*a,**kw):raise RuntimeError('018 verification: network forbidden')
    socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
    for name in ('preparation_001','analysis_001','review_001','diagnosis_001','trace_001'):c.check(c.OUT/name)
    rows=c.jsonlines(c.OUT/'preparation_001/ledger.jsonl')
    cohorts=c.csvrows(c.TEN/'preparation_001/cohort.csv')+c.csvrows(c.SIXTEEN/'stage1/preparation_002/cohort.csv')
    validate_rows(rows,cohorts)
    order=c.prior.old.baseline.patient_order()
    for q,group,n in [('010',order[18:24],650),('016',order[24:30],601)]:
        rr=[r for r in rows if r['cohort']==q]
        c.require(len(rr)==n and {r['subject_id'] for r in rr}==set(group),'Patient isolation')
    # Bind predictions directly to all six formal historical exports, without recomputing labels.
    for q,s,path in [('010','O',c.TEN/'preparation_001/released_predictions.csv'),('010','C',c.TEN/'analysis_001/predictions_c48_reference.csv'),('010','V',c.TEN/'analysis_001/predictions_verifact_reference.csv'),('016','O',c.SIXTEEN/'completion_002/analysis_001/predictions_released.csv'),('016','C',c.SIXTEEN/'completion_002/analysis_001/predictions_v4_first.csv'),('016','Q',c.SIXTEEN/'completion_002/analysis_001/predictions_qwen.csv')]:
        pp=c.csvrows(path);byid={p['proposition_id']:p['verdict'] for p in pp};rr=[r for r in rows if r['cohort']==q]
        c.require(len(pp)==len(byid)==len(rr) and set(byid)=={r['proposition_id'] for r in rr},'Historical prediction inventory')
        c.require(all(r[s]==byid[r['proposition_id']] for r in rr),'Historical predictions changed')
    notes,_,anchors=load_notes();c.require(len(notes)==78 and not any(not x['found'] for x in anchors),'Anchor check')
    priority=c.read(c.OUT/'review_001/deep_priority.json')
    c.require(set(priority['reasons'])=={n['case_id'] for n in notes},'Reading coverage mismatch')
    before=c.read(c.OUT/'history_before.json');changed=[];protected=0
    for name,sha in before['files'].items():
        if name in NAV:continue
        c.require(c.file_hash(c.ROOT/name)==sha,'Historical file changed: '+name);protected+=1
    out.mkdir(parents=True)
    analyze(out/'analysis_001');diagnose(out/'diagnosis_001');trace(out/'trace_001')
    counts={name:equal_contents(c.OUT/name,out/name) for name in ('analysis_001','diagnosis_001','trace_001')}
    summary=dict(status='executor_offline_checks_pass_not_independent_audit',claims=1251,patients=12,semantic_cases=78,literal_anchors=len(anchors),replayed_content_files=counts,protected_historical_files=protected,network_blocked=True,new_API_calls=0,cost_cny=0)
    c.write_json(out/'summary.json',summary)
    c.seal(out,[c.OUT/'history_before.json'],[Path(__file__)])
    print(c.canonical(summary))

def handoff():
    c.require(not (c.OUT/'handoff_001.json').exists(),'Handoff exists')
    files={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for folder in (c.TASK,c.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    files.update({n:c.file_hash(c.ROOT/n) for n in NAV})
    c.write_json(c.OUT/'handoff_001.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),files=files,status='ready_for_independent_audit_not_PASS',new_API_calls=0,cost_cny=0))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'verification_001');p.add_argument('--handoff',action='store_true');a=p.parse_args()
    handoff() if a.handoff else verify(a.output)
