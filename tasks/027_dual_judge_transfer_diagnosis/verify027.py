"""Executor independent arithmetic checks; not an independent research audit."""
import argparse,collections,re,subprocess,sys
from pathlib import Path
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint,linprog
import common027 as x
import analyze027_saved as analysis

def run(destination):
    x.offline();out=Path(destination).resolve();x.c.require(not out.exists(),'New verification directory required');a=x.OUT/'analysis_002';checks={}
    def ck(name,v):checks[name]=bool(v);x.c.require(bool(v),'Check failed: '+name)
    for folder in ('analysis_001','analysis_002','case_material_001','reading_view_001','semantic_001','interpretation_001'):
        m=x.read(x.OUT/folder/'manifest.json')
        for name,h in m['inputs'].items():ck(folder+' input '+name,x.sha(x.ROOT/name)==h)
        for name,h in m['outputs'].items():ck(folder+' output '+name,x.sha(x.OUT/folder/name)==h)
    for number,name in [('025','025_lambda_flip_risk_separability'),('026','026_frozen_sd_patient_transfer')]:
        previous=x.ROOT/'outputs'/name/('analysis_003' if number=='025' else 'analysis_001');m=x.read(previous/'manifest.json');od=m['outputs'] if number=='025' else m['outputs_sha256']
        ck(number+' frozen analysis preserved',all(x.sha(previous/n)==h for n,h in od.items()))
    gf=x.ROOT/'outputs/026_frozen_sd_patient_transfer/gate_freeze/manifest.json'
    ck('gate source freeze preserved',all(x.sha(x.ROOT/p)==h for p,h in x.read(gf)['sha256'].items()))
    groups,items,gate=analysis.load();canonical=x.read(a/'candidates.json');ck('candidate source rebuild',items==canonical)
    old=x.read(x.OUT/'analysis_001/candidates.json');ck('only_saved_prob_roundoff',all({k:v for k,v in r.items() if k!='SD'}=={k:v for k,v in z.items() if k!='SD'} and abs(r['SD']-z['SD'])<1e-12 for r,z in zip(old,items)))
    ck('frozen training patient disjoint',set(gate['training_patients']).isdisjoint(r['subject_id'] for r in groups['026'][0]))
    # Direct pairwise AUC with half credit for ties.
    rank=x.c.csvrows(a/'ranking.csv')
    for group,(_,its) in groups.items():
        for method in analysis.base.METHODS:
            r=[z[method] for z in its if z['kind']=='R'];f=[z[method] for z in its if z['kind']!='R'];auc=sum((p>q)+.5*(p==q) for p in r for q in f)/(len(r)*len(f));published=float(next(z['AUROC'] for z in rank if z['group']==group and z['method']==method and z['scope']=='all'));ck('pairwise AUC '+group+method,abs(auc-published)<1e-12)
    curves=x.c.csvrows(a/'curves.csv');anchors=x.c.csvrows(a/'high_rescue.csv')
    for group,(full,its) in groups.items():
        byid={r['proposition_id']:r for r in its}
        for method in analysis.base.METHODS:
            for j,row in enumerate(z for z in curves if z['group']==group and z['method']==method):
                t=float(row['threshold']);keep=[r for r in its if r[method]>=t];R=sum(r['kind']=='R' for r in keep);H=sum(r['kind']=='H' for r in keep);W=sum(r['kind']=='W' for r in keep)
                ck(f'curve {group} {method} {j}',(R,H,W)==(int(row['R']),int(row['H']),int(row['W'])))
                pred=np.array([0 if r['candidate'] and byid[r['proposition_id']][method]>=t else r['u0'] for r in full]);m=x.c.point(full,pred)
                ck(f'002 {group} {method} {j}',all(abs(float(row[k])-m[k])<1e-12 for k in ('PA','MCC','AC1','correct','false_S','S_recall','NS_recall','NA_recall')))
        for row in (z for z in anchors if z['group']==group):
            rr=[z for z in curves if z['group']==group and z['method']==row['method'] and int(z['R'])>=int(row['target_R'])];ck('target '+group+row['method']+row['target_retention'],min(int(z['risk']) for z in rr)==int(row['risk']))
        # Full global matching to already audited history, including every lambda state.
        new=[r for r in x.c.csvrows(a/'global_curves.csv') if r['group']==group]
        oldpath=x.ROOT/('outputs/025_lambda_flip_risk_separability/analysis_003/global_lambda_curves.csv' if group=='025' else 'outputs/026_frozen_sd_patient_transfer/analysis_001/global_frontier.csv')
        oldglobal=[r for r in x.c.csvrows(oldpath) if (r.get('group')=='024_D' and r.get('author')=='all') or (r.get('scope')=='primary_common' and r.get('author')=='all')]
        ck('full global count '+group,len(new)==len(oldglobal));ck('full global audited agreement '+group,all(all(abs(float(n[k])-float(o[k]))<1e-12 for k in ('lambda_value','correct','PA','MCC','R','risk','false_S')) for n,o in zip(new,oldglobal)))
        risks=np.array([float(r['risk']) for r in new]);rescues=np.array([float(r['R']) for r in new])
        for row in (z for z in anchors if z['group']==group and z['method']=='SD'):
            sol=linprog(-rescues,A_ub=risks[None,:],b_ub=[float(row['risk'])],A_eq=np.ones((1,len(risks))),b_eq=[1],bounds=(0,None),method='highs');ck('full mixture LP '+group+row['target_retention'],sol.success and abs(float(row['actual_R'])+sol.fun-float(row['gain_vs_global_mixture']))<1e-8)
    conflict=x.read(a/'conflicts.json')
    for group,its in [('025',groups['025'][1]),('026',groups['026'][1]),('pooled_descriptive',items)]:
        gg=collections.defaultdict(list)
        for r in its:gg[tuple(r['features'][k] for k in x.c.METHODS['SD'])].append(r)
        R=np.array([sum(r['kind']=='R' for r in v) for v in gg.values()],dtype=float);F=np.array([sum(r['kind']!='R' for r in v) for v in gg.values()],dtype=float)
        for target,minimum in conflict[group]['oracle_min_risk_at_retention'].items():
            n=int(np.ceil(float(target)*sum(R)-1e-10));sol=milp(c=F,integrality=np.ones(len(R)),bounds=Bounds(0,1),constraints=LinearConstraint(R[None,:],lb=[n],ub=[np.inf]));ck('group oracle MILP '+group+target,sol.success and abs(sol.fun-minimum)<1e-8)
        ck('group error lower bound '+group,int(np.minimum(R,F).sum())==conflict[group]['unavoidable_binary_errors'])
    selected=x.read(a/'case_selection.json');ledger=x.read(x.OUT/'semantic_001/case_ledger.json');ck('case selection saved-prob invariant',selected==x.read(x.OUT/'analysis_001/case_selection.json'));ck('31 cases all read',len(ledger)==len(selected)==31 and all(r['full_packet_read'] for r in ledger));ck('17 error cases',sum(r['role']=='error' for r in ledger)==17)
    for r in ledger:
        material=x.read(x.OUT/'case_material_001'/(r['case_id']+'.json'));ck('case source '+r['case_id'],x.sha(x.OUT/'case_material_001'/(r['case_id']+'.json'))==r['source_sha256']);ck('quote offsets '+r['case_id'],all(material['reference'][v['start']:v['end']]==v['quote'] for v in r['anchors']))
    unit=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(x.TASK),'-p','test*.py','-v'],cwd=x.ROOT,text=True,capture_output=True);ck('unit tests',unit.returncode==0)
    out.mkdir(parents=True);x.put(out/'checks.json',dict(executor_self_check=True,independent_audit=False,passed=len(checks),checks=checks,API_calls=0,new_fits=0));(out/'unit_tests.txt').write_text(unit.stdout+unit.stderr,encoding='utf-8')
    x.put(out/'manifest.json',dict(inputs={p.relative_to(x.ROOT).as_posix():x.sha(p) for p in [Path(__file__),x.TASK/'test027.py',a/'manifest.json']},outputs={p.name:x.sha(p) for p in out.iterdir() if p.is_file()}));print('027 execution self-check passed',len(checks))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');a=p.parse_args();run(a.destination)
