"""Executor arithmetic, freeze, quote, and LP self-check; not independent audit."""
import argparse,json,re,subprocess,sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
import numpy as np
from scipy.optimize import linprog
import common028 as c
import analyze028 as analysis

def run(destination):
    out=Path(destination).resolve();c.require(not out.exists(),'New verification directory required');jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);a=c.OUT/'analysis_001';checks={}
    def ck(name,v):checks[name]=bool(v);c.require(bool(v),'Self-check failed: '+name)
    for folder in ('analysis_001','diagnosis_001','semantic_001'):
        m=c.read(c.OUT/folder/'manifest.json')
        ck(folder+' inputs',all(c.sha(c.ROOT/p)==h for p,h in m['inputs'].items()));ck(folder+' outputs',all(c.sha(c.OUT/folder/p)==h for p,h in m['outputs'].items()))
    ck('one HTTP200 per job',len(attempts)==len(term)==len(jobs)==310);ck('all core valid',all(v['status'] in c.VALID for v in term.values()))
    materials={r['proposition_id']:r for r in c.lines(c.OUT/'preparation_001/materials.jsonl')};candidates={r['proposition_id']:r for r in c.read(c.OUT/'preparation_001/candidates.json')};fees=Decimal(0);first=None;reserve=[]
    for j in jobs:
        mat=materials[j['proposition_id']];ck('body '+j['request_id'],j['body']==c.body(mat['text'],mat['reference'],j['arm']));ck('only claim reference '+j['request_id'],json.loads(j['body']['messages'][1]['content'])==dict(proposition=mat['text'],reference=mat['reference']))
        path=c.OUT/'attempts'/(j['request_id']+'_01');rq=c.read(path/'request.json');tr=c.read(path/'receipt.json')['transport'];v=json.loads(tr['body_text']);ck('model '+j['request_id'],v['model']==c.MODEL);ck('budget '+j['request_id'],rq['prior_task_used_or_reserved_cny']+rq['reservation_cny']<=80);reserve.append(rq['prior_task_used_or_reserved_cny']+rq['reservation_cny']);first=min(first,rq['created_utc']) if first else rq['created_utc'];u=v['usage'];fees+=(Decimal(u['prompt_tokens'])*3+Decimal(u['completion_tokens'])*9)/1000000
        parsed=term[j['request_id']]
        if j['arm']=='trace':
            obj=json.loads(v['choices'][0]['message']['content']);parts=re.split(r'(?m)(?=^\d+\. Date:)',mat['reference']);entries={int(re.match(r'(\d+)\.',part).group(1)):part for part in parts if re.match(r'\d+\. Date:',part)};norm=lambda text:' '.join(text.split())
            grounded=True;semantic=obj['claim_coverage']=='complete' and bool(obj['requirements'])
            for r in obj['requirements']:
                semantic=semantic and r['relation']=='supported';grounded=grounded and bool(r['claim_quote'].strip()) and norm(r['claim_quote']) in norm(mat['text']) and bool(r['evidence']) and all(e['reference_id'] in entries and bool(e['quote'].strip()) and norm(e['quote']) in norm(entries[e['reference_id']]) for e in r['evidence'])
            ck('independent trace keep '+j['request_id'],bool(semantic and grounded)==parsed['keep'])
    ck('frozen before API',c.read(c.OUT/'preparation_001/manifest.json')['created_utc']<first);ck('Decimal fee',abs(float(fees)-c.read(a/'costs.json')['total_cny'])<1e-12)
    _,_,_,rows=analysis.load();pred=c.csvread(a/'predictions.csv');metrics=c.read(a/'metrics.json');curves=c.csvread(a/'curves.csv');summary=c.read(a/'matched.json')
    for group in ('025','026','pooled'):
        rr=[r for r in pred if group=='pooled' or r['group']==group]
        for author in ('all','human','llm'):
            ss=[r for r in rr if author=='all' or r['author_type']==author]
            for name in ('U0','U2','SD','repeat','trace'):
                m=metrics[group+'/'+author+'/'+name];cm=[[sum(r['GT']==g and r[name]==p for r in ss) for p in c.LABELS] for g in c.LABELS];ck('CM '+group+author+name,cm==m['confusion_matrix']);ck('correct '+group+author+name,sum(cm[i][i] for i in range(3))==m['correct'])
                R=sum(r['GT']=='Supported' and r['U0']!='Supported' and r[name]=='Supported' for r in ss);H=sum(r['GT']!='Supported' and r['GT']==r['U0'] and r[name]=='Supported' for r in ss);W=sum(r['GT']!='Supported' and r['U0'] not in ('Supported',r['GT']) and r[name]=='Supported' for r in ss);ck('RHW '+group+author+name,(R,H,W)==(m['R'],m['H'],m['W']))
        for ref in ('global_lambda','SD','repeat'):
            cc=[r for r in curves if r['group']==group and r['reference']==ref];rs=np.array([float(r['R']) for r in cc]);fs=np.array([float(r['risk']) for r in cc]);target=metrics[group+'/all/trace'];lp=linprog(-rs,A_ub=fs[None,:],b_ub=[target['risk']],A_eq=np.ones((1,len(rs))),b_eq=[1],bounds=(0,None),method='highs');ck('LP '+group+ref,lp.success and abs(target['R']+lp.fun-summary[group]['matched'][ref]['R_gain_vs_mixture'])<1e-8)
        full=[r for r in rows if group=='pooled' or r['group']==group];refs,_,_=analysis.references(full)
        for entry in summary[group]['leave_one_patient_out']:
            w=np.array([float(r['subject_id']!=entry['excluded_patient']) for r in full]);targetR,targetF=c.frontier.counts(full,np.array([r['trace'] for r in full]),w)
            for name,pp in refs.items():
                rr,ff=c.frontier.counts(full,pp,w);lp=linprog(-rr,A_ub=ff[None,:],b_ub=[targetF[0]],A_eq=np.ones((1,len(rr))),b_eq=[1],bounds=(0,None),method='highs');ck('LOO LP '+group+entry['excluded_patient']+name,lp.success and abs(targetR[0]+lp.fun-entry['comparisons'][name]['R_gain_vs_mixture'])<1e-8)
    # Original clinical packets are exactly reused, not amended by source diagnosis.
    for i,key in enumerate(('C06','C16','C14','C29'),1):
        old=c.read(c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/case_material_001'/(key+'.json'));new=c.read(c.OUT/'diagnosis_001'/f'K{i:02}.json');ck('old packet '+key,old['claim']==new['claim'] and old['reference']==new['reference'])
    for r in c.read(c.OUT/'semantic_001/case_ledger.json'):
        packet=c.read(c.OUT/'diagnosis_001'/(r['case_id']+'.json'));ck('semantic anchor '+r['case_id'],all(packet['reference'][a['start']:a['end']]==a['quote'] for a in r['anchors']))
    for r in c.read(c.OUT/'semantic_001/evidence_source_checks.json'):
        packet=c.read(c.ROOT/r['source']);ck('extra source anchor '+r['case_id'],all(packet['reference'][a['start']:a['end']]==a['quote'] for a in r['hits']))
    original=c.read(c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002/conflicts.json');conf=c.read(a/'conflicts.json');pm={r['proposition_id']:r for r in pred}
    for group in ('025','026'):
        ids={p for g in original[group]['mixed_groups'] for p in g['ids']}
        for method in ('SD','repeat','trace'):ck('conflict errors '+group+method,sum((pm[p][method]=='Supported')!=(pm[p]['GT']=='Supported') for p in ids)==conf[group]['methods'][method]['binary_errors'])
    units=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(c.TASK),'-p','test*.py','-v'],cwd=c.ROOT,text=True,capture_output=True);ck('unit tests',units.returncode==0)
    tracked=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();ck('historical tracked files unchanged',set(tracked)<={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md'})
    out.mkdir(parents=True);c.put(out/'checks.json',dict(executor_self_check=True,independent_audit=False,passed=len(checks),checks=checks,Decimal_usage_cost_cny=str(fees),max_registered_used_plus_inflight=max(reserve)));(out/'unit_tests.txt').write_text(units.stdout+units.stderr,encoding='utf-8')
    c.put(out/'manifest.json',dict(inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [Path(__file__),c.TASK/'test028.py',a/'manifest.json']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('028 self-checks passed',len(checks),'cost',fees)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
