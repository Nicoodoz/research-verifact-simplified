"""Independent decode/source checks and network-blocked replay into a fresh directory."""
from pathlib import Path
import argparse,math,socket,subprocess
from collections import Counter
import common022 as c
from analyze022 import run
from budget022 import total

def verify(out):
    c.require(not out.exists(),'Verification directory exists')
    def blocked(*args,**kwargs):raise RuntimeError('022 offline replay blocks network')
    socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
    c.check(c.OUT/'preparation_001');c.check(c.OUT/'stageA_002')
    rows=c.jl(c.OUT/'preparation_001/rows.jsonl');oof=c.jl(c.OUT/'stageA_002/oof_predictions.jsonl')
    bykey={(r['proposition_id'],r['repeat'],r['method']):r for r in oof}
    c.require(len(bykey)==len(oof)==24080,'OOF uniqueness/completeness')
    fits=c.read(c.OUT/'stageA_002/fitted_parameters.json');fit={(r['fold'],r['method']):r for r in fits}
    source={p:{r['request_id']:r for r in c.jl(c.ROOT/p)} for p in {r['normalized_source'] for r in rows}}
    evidence={};provenance=[];deps=[]
    for task,folder in [('019','019_support_boundary_screen/selection/preparation'),('020','020_lambda2_patient_validation/new10/base_preparation_001')]:
        root=c.ROOT/'outputs'/folder;path=root/'inputs.jsonl';man=c.read(root/'manifest.json')['sha256'];c.require(c.sha(path)==man[path.relative_to(c.ROOT).as_posix()],'C48 input changed')
        deps.extend([path,root/'manifest.json']);evidence[task]={r['proposition_id']:r for r in c.jl(path)}
    for r in rows:
        pid=r['proposition_id'];normal=source[r['normalized_source']][r['scoring_request_id']]
        c.require(normal['scores']==r['scores'] and normal['verdict']==r['V_raw'],'Source mismatch')
        raw={label:max(r['scores'][label]/100,1e-6) for label in c.LABELS};order=(c.LABELS[1],c.LABELS[2],c.LABELS[0])
        u0=max(order,key=lambda label:raw[label]);u2=max(order,key=lambda label:raw[label]*(math.exp(2) if label=='Supported' else 1))
        c.require(bykey[(pid,r['repeat'],'U0')]['verdict']==u0 and bykey[(pid,r['repeat'],'U2')]['verdict']==u2,'Independent U0/U2 decode')
        ca=fit[(r['fold'],'C')];ratio=raw['Not Supported']/(raw['Not Supported']+raw['Not Addressed']);bias=ratio*ca['theta'][0]+(1-ratio)*ca['theta'][1]
        cv=max(order,key=lambda label:raw[label]*(math.exp(bias) if label=='Supported' else 1));c.require(cv==bykey[(pid,r['repeat'],'C')]['verdict'],'Independent competition decode')
        for method in c.LEARNED:
            f=fit[(r['fold'],method)]
            c.require(r['subject_id'] not in f['train_patients'] and r['subject_id'] in f['test_patients'],'Patient leak')
            pred=bykey[(pid,r['repeat'],method)];c.require(pred['score_request_id']==r['scoring_request_id'],'Different methods used different scoring answers')
            c.require(len(pred['probabilities'])==3 and abs(sum(pred['probabilities'])-1)<1e-12,'Probability normalization')
        if r['repeat']==0:
            ev=evidence[r['source']][pid];c.require(ev['subject_id']==r['subject_id'] and ev['author_type']==r['author_type'],'Evidence patient binding')
            provenance.append(dict(proposition_id=pid,subject_id=r['subject_id'],source=r['source'],claim_sha256=c.digest(ev['text']),reference_sha256=c.digest(ev['reference']),input_file=('outputs/'+('019_support_boundary_screen/selection/preparation' if r['source']=='019' else '020_lambda2_patient_validation/new10/base_preparation_001')+'/inputs.jsonl')))
    for f in fits:
        expected=[r['scoring_request_id'] for r in rows if r['repeat']==0 and r['fold']!=f['fold']]
        c.require(f['train_scoring_ids']==expected and len(expected)==f['train_claims'],'Repeat weighting/source train list')
    budget=c.read(c.OUT/'stageA_002/budget.json');c.require(total(budget['attempts'])==0 and budget['new_calls']==0,'Offline budget')
    out.mkdir(parents=True);run(out/'replay')
    ref=c.OUT/'stageA_002';paths=[p for p in ref.iterdir() if p.is_file() and p.name!='manifest.json']
    for p in paths:c.require(p.read_bytes()==(out/'replay'/p.name).read_bytes(),'Replay mismatch: '+p.name)
    # Frozen source hash snapshots cover source answers andC48; git diff must only expose navigation changes.
    changed=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines()
    allowed={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','docs/aliyun/CURRENT.md','reviews/README.md','.gitattributes'}
    c.require(set(changed)<=allowed,'Unexpected historical tracked change')
    c.csvwrite(out/'evidence_provenance.csv',provenance)
    summary=dict(status='executor_checks_pass_not_independent_audit',source_score_observations=len(rows),unique_claims=len(provenance),oof_rows=len(oof),independent_decodes=len(rows)*3,replayed_files=len(paths),network_blocked=True,new_API_calls=0,cost_cny=0,C_G_different_labels=sum(bykey[(r['proposition_id'],r['repeat'],'C')]['verdict']!=bykey[(r['proposition_id'],r['repeat'],'G')]['verdict'] for r in rows))
    c.write(out/'summary.json',summary);c.seal(out,deps,[Path(__file__),c.TASK/'budget022.py']);print(c.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'verification_001');verify(p.parse_args().output)
