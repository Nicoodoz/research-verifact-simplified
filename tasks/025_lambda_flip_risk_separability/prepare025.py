"""Bind audited frozen score tables and GT-blind reference features; no raw dataset reads."""
import subprocess
from collections import Counter
import common025 as c
def run():
    out=c.OUT/'preparation_001';out.mkdir(parents=True,exist_ok=False)
    deps=[c.OUT/'protocol_001.md'];allrows=[];groups={};material_paths={}
    for source,n,reps in [('019_support_boundary_screen',650,1),('020_lambda2_patient_validation',879,2)]:
        root=c.ROOT/'outputs'/source;old=source.startswith('019');analysis=root/('selection/analysis_001' if old else 'analysis_001');prep=root/('selection/preparation' if old else 'new10/base_preparation_001')
        cp=root/('selection/cohort.csv' if old else 'new10/preparation_002/cohort.csv');ip=prep/'inputs.jsonl'
        rows=c.csvrows(cp);materials={r['proposition_id']:r for r in c.jl(ip)};normpath=analysis/'normalized.jsonl';nn={r['request_id']:r for r in c.jl(normpath)};assign=c.csvrows(prep/'assignments.csv');aa={(r['proposition_id'],int(r['repeat']),r['arm']):r for r in assign}
        for path,man in [(normpath,analysis/'manifest.json'),(ip,prep/'manifest.json')]:c.require(c.sha(path)==c.read(man)['sha256'][path.relative_to(c.ROOT).as_posix()],'Frozen source changed')
        deps.extend([cp,ip,normpath,prep/'assignments.csv',analysis/'manifest.json',prep/'manifest.json'])
        features={pid:c.evidence_features(m) for pid,m in materials.items()}
        for rep in range(reps):
            pp=analysis/f'predictions_r{rep}.csv';pred={r['proposition_id']:r for r in c.csvrows(pp)};deps.append(pp)
            group='019' if old else f'020_R{rep}';groups[group]=[]
            for r in rows:
                pid=r['proposition_id'];s=nn[aa[(pid,rep,'S')]['request_id']];c.require(s['status']=='success','Invalid frozen scoring')
                sc=s['scores'];z=c.logs(sc);u0=int(c.decode(z,0));u2=int(c.decode(z,2))
                c.require(c.LABELS[u0]==pred[pid]['U0'] and c.LABELS[u2]==pred[pid]['U_lambda_2' if old else 'U2'],'Historical anchor mismatch')
                row=dict(proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],group=group,scores=sc,u0=u0,u2=u2,B=pred[pid]['B'],candidate=u0!=0 and u2==0,features={**c.score_features(sc),**features[pid]},evidence_retrieval_available=not old)
                groups[group].append(row)
            c.require(len(groups[group])==n,'Unexpected cohort size')
        if not old:newmaterial=materials;newfeatures=features
    root=c.ROOT/'outputs/024_lambda2_transfer_validation';pp={};manifest=c.read(root/'analysis_001/manifest.json')
    for model in ('deepseek','qwen'):
        path=root/f'analysis_001/predictions_{model}.csv';c.require(c.sha(path)==manifest['outputs_sha256'][path.name],'024 predictions changed');deps.append(path);pp[model]=c.csvrows(path)
    deps.append(root/'analysis_001/manifest.json')
    for model,peer in [('deepseek','qwen'),('qwen','deepseek')]:
        group='024_D' if model=='deepseek' else '024_Q';other={r['proposition_id']:r for r in pp[peer]};groups[group]=[]
        for r in pp[model]:
            pid=r['proposition_id'];s={k:int(r['score_'+k]) for k in c.LABELS};q={k:int(other[pid]['score_'+k]) for k in c.LABELS};u0=int(c.decode(c.logs(s),0));u2=int(c.decode(c.logs(s),2));q0=int(c.decode(c.logs(q),0));q2=int(c.decode(c.logs(q),2))
            c.require(c.LABELS[u0]==r['U0'] and c.LABELS[u2]==r['U2'],'024 anchor mismatch');c.require(all(r[k]==other[pid][k] for k in ('subject_id','author_type','human_gt')),'Cross-model identity mismatch')
            d=dict(zip(c.D_NAMES,[q[c.LABELS[0]]/100,c.logs(q)[0]-max(c.logs(q)[1:]),float(q0==0),float(q2==0),float(q0==u0)]))
            groups[group].append(dict(proposition_id=pid,subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],group=group,scores=s,u0=u0,u2=u2,B=r['B'] or None,candidate=u0!=0 and u2==0,peer_u2=q2,features={**c.score_features(s),**newfeatures[pid],**d},evidence_retrieval_available=True))
    c.require(set(r['subject_id'] for r in groups['019']).isdisjoint(r['subject_id'] for r in groups['024_D']),'Cohort patient overlap')
    for group,rr in groups.items():
        c.require(len(set(r['proposition_id'] for r in rr))==len(rr),'Duplicate claim')
        for r in rr:
            c.require(all(type(v) is int and 0<=v<=100 for v in r['scores'].values()) and sum(r['scores'].values())==100,'Invalid score')
        allrows.extend(rr)
    summary={g:dict(n=len(rr),patients=len(set(r['subject_id'] for r in rr)),candidate=sum(r['candidate'] for r in rr),R=sum(r['candidate'] and r['human_gt']=='Supported' for r in rr),risk=sum(r['candidate'] and r['human_gt']!='Supported' for r in rr)) for g,rr in groups.items()}
    probes={}
    for g,expected in [('024_D',(46,5)),('024_Q',(18,2))]:
        rr=[r for r in groups[g] if r['candidate'] and r['peer_u2']==0];got=(sum(r['human_gt']=='Supported' for r in rr),sum(r['human_gt']!='Supported' for r in rr));c.require(got==expected,'User probe check differs; investigate alignment')
        probes[g]=dict(R=got[0],risk=got[1],status='025 new exploratory baseline; not024 audited method')
    c.lines(out/'rows.jsonl',allrows);c.write(out/'summary.json',summary);c.write(out/'probe_checks.json',probes)
    c.write(out/'source_manifest.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps},features=c.METHODS,new_API_calls=0,cost_cny=0))
    c.write(out/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in list(out.iterdir())+[c.TASK/'common025.py',c.TASK/'prepare025.py',c.OUT/'protocol_001.md']}))
    print(c.canonical(summary));print(c.canonical(probes))
if __name__=='__main__':run()
