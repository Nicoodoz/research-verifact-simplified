"""First reserved GT join after the complete blinded prediction seal."""
import sys
import numpy as np
import pandas as pd
import common036 as c
sys.path.insert(0,str(c.ROOT/'tasks/035_lambda_boundary_calibration'))
import common as old
import analysis as a

def point(rr,p,lp=None):
    if lp is not None:return a.point(rr,p,lp)
    m=old.evaluate(old.cohort(rr),old.predictions(rr,p),profile='none');cm=np.array(m['confusion_matrix'])
    return dict(n=len(rr),correct=int(np.trace(cm)),PA=m['percent_agreement'],MCC=m['mcc'],AC1=m['gwet_ac1'],false_S=int(cm[1:,0].sum()),non_S=int(cm[1:].sum()),FSR=float(cm[1:,0].sum()/cm[1:].sum()) if cm[1:].sum() else None,S_recall=m['per_class']['Supported']['recall'],NS_recall=m['per_class']['Not Supported']['recall'],NA_recall=m['per_class']['Not Addressed']['recall'],confusion_matrix=cm.tolist(),per_class=m['per_class'])
def risk_extra(rr,b,p):
    subjects=sorted(set(r['sid'] for r in rr));g=len(subjects);gi=np.array([subjects.index(r['sid']) for r in rr]);y=np.array([r['y'] for r in rr]);weights=np.stack([np.bincount(np.random.RandomState(i).choice(g,g),minlength=g) for i in range(1000)])
    delta=((p==0)&(y!=0)).astype(float)-((b==0)&(y!=0));num=np.bincount(gi,weights=delta,minlength=g);den=np.bincount(gi,weights=y!=0,minlength=g);dd=weights@den;vv=(weights@num)[dd>0]/dd[dd>0]
    return dict(delta=float(delta.sum()/den.sum()) if den.sum() else None,ci95=np.quantile(vv,[.025,.975]).tolist() if len(vv) else None)
def analyze(name,allrows,folder):
    methods=c.read(c.OUT/'final_freeze_001/config.json')['methods'];available={m:[r for r in allrows if r['methods'].get(m,{}).get('label') is not None] for m in methods}
    coverage=[dict(method=m,total_n=len(allrows),valid_n=len(rr),missing_n=len(allrows)-len(rr),missing_ids=[r['id'] for r in allrows if r not in rr],correct_available=sum(r['methods'][m]['label']==r['y'] for r in rr),PA_total_missing_as_error=sum(r['methods'][m]['label']==r['y'] for r in rr)/len(allrows)) for m,rr in available.items()]
    rows=[r for r in allrows if all(r['methods'].get(m,{}).get('label') is not None for m in methods)];assert rows
    output={m:(np.array([r['methods'][m]['label'] for r in rows]),np.array([r['methods'][m]['logprob'] for r in rows]) if all('logprob' in r['methods'][m] for r in rows) else None) for m in methods}
    y=np.array([r['y'] for r in rows]);tables=[];detailed={};pairs={};patients=[];reliability=[];transitions=[];directions=[];risk=[];breakdown=[]
    pair_defs=c.read(c.OUT/'final_freeze_001/config.json')['primary_pairs']+[[m,'U2'] for m in ('Std_T','Std_G','Std_M','Std_V','Joint_NLL','MCC_T')]
    for scope in ('all','human','llm'):
        ii=np.array([i for i,r in enumerate(rows) if scope=='all' or r['author']==scope]);rr=[rows[i] for i in ii]
        for m,(p,lp) in output.items():
            mm=point(rr,p[ii],lp[ii] if lp is not None else None);detailed[scope+'/'+m]=mm;tables.append(dict(dataset=name,scope=scope,method=m,**{k:v for k,v in mm.items() if k not in ('confusion_matrix','per_class')}))
        for new,base in pair_defs:
            bp,bl=output[base];np_,nl=output[new];pair=old.paired_compare(old.cohort(rr),old.predictions(rr,bp[ii]),old.predictions(rr,np_[ii]),iterations=1000)
            pair['false_S_rate']=risk_extra(rr,bp[ii],np_[ii])
            if bl is not None and nl is not None:pair['probability_and_risk']=a.paired_extra(rr,(bp[ii],bl[ii]),(np_[ii],nl[ii]))
            pairs[scope+'/'+new+'-vs-'+base]=pair
        for m,(p,_) in output.items():
            u0=output['U0'][0][ii];u2=output['U2'][0][ii];gt=y[ii];pred=p[ii];cand=(u0!=0)&(u2==0);accepted=cand&(pred==0)
            R=int(np.sum(accepted&(gt==0)));H=int(np.sum(accepted&(gt!=0)&(u0==gt)));W=int(np.sum(accepted&(gt!=0)&(u0!=gt)));totalR=int(np.sum(cand&(gt==0)))
            risk.append(dict(dataset=name,scope=scope,method=m,candidate_n=int(cand.sum()),R=R,H=H,W=W,new_false_S=H+W,total_R=totalR,rescue_retention=R/totalR if totalR else None,total_false_S=int(np.sum((pred==0)&(gt!=0))),correct=int(np.sum(pred==gt)),note='R/H/W restricted to original U2 candidates; general classifiers may additionally change noncandidates'))
    for sid in sorted(set(r['sid'] for r in rows)):
        ii=np.array([i for i,r in enumerate(rows) if r['sid']==sid]);rr=[rows[i] for i in ii]
        for m,(p,lp) in output.items():
            v=point(rr,p[ii],lp[ii] if lp is not None else None)
            patients.append(dict(dataset=name,sid=sid,method=m,**{k:v for k,v in v.items() if k not in ('confusion_matrix','per_class')},delta_correct_vs_U2=int(np.sum(p[ii]==y[ii])-np.sum(output['U2'][0][ii]==y[ii]))))
    for new,base in pair_defs:
        bp=output[base][0];p=output[new][0];d=(p==y).astype(int)-(bp==y).astype(int);by={sid:int(d[[r['sid']==sid for r in rows]].sum()) for sid in sorted(set(r['sid'] for r in rows))}
        directions.append(dict(comparison=new+'-vs-'+base,positive=sum(x>0 for x in by.values()),negative=sum(x<0 for x in by.values()),tied=sum(x==0 for x in by.values()),net=int(d.sum()),largest_patient_gain=max(by.values()),largest_patient_loss=min(by.values()),leave_one_out_min_net=int(d.sum()-max(by.values())),leave_one_out_max_net=int(d.sum()-min(by.values())),patient_deltas=by))
        for i,r in enumerate(rows):
            if p[i]!=bp[i]:transitions.append(dict(comparison=new+'-vs-'+base,id=r['id'],sid=r['sid'],author=r['author'],GT=c.LABELS[y[i]],baseline=c.LABELS[bp[i]],candidate=c.LABELS[p[i]],fix=int(bp[i]!=y[i] and p[i]==y[i]),harm=int(bp[i]==y[i] and p[i]!=y[i]),new_false_S=int(y[i]!=0 and bp[i]!=0 and p[i]==0),prevented_false_S=int(y[i]!=0 and bp[i]==0 and p[i]!=0)))
    for m,(p,lp) in output.items():
        if lp is None:continue
        q=np.exp(lp)
        for cls,label in enumerate(c.LABELS):
            bins=np.minimum((q[:,cls]*10).astype(int),9)
            for k in range(10):
                mask=bins==k;reliability.append(dict(method=m,label=label,bin=k,n=int(mask.sum()),mean_probability=float(q[mask,cls].mean()) if mask.any() else None,frequency=float((y[mask]==cls).mean()) if mask.any() else None))
        raw=np.array([[r['scores'][label] for label in c.LABELS] for r in rows]);masks={'U2_correct':output['U2'][0]==y,'U2_wrong':output['U2'][0]!=y,'GT_score_zero':raw[np.arange(len(y)),y]==0}
        for group,mask in masks.items():breakdown.append(dict(method=m,group=group,n=int(mask.sum()),NLL=float(-lp[mask,y[mask]].mean()) if mask.any() else None,Brier=float(((q[mask]-np.eye(3)[y[mask]])**2).sum(1).mean()) if mask.any() else None))
    c.csvwrite(folder/'coverage.csv',coverage);c.csvwrite(folder/'metrics.csv',tables);c.put(folder/'metrics.json',detailed);c.put(folder/'paired.json',pairs);c.csvwrite(folder/'patients.csv',patients);c.put(folder/'directions.json',directions);c.csvwrite(folder/'risk_rescue.csv',risk);c.csvwrite(folder/'transitions.csv',transitions);c.csvwrite(folder/'reliability.csv',reliability);c.csvwrite(folder/'probability_breakdown.csv',breakdown)
    c.csvwrite(folder/'predictions.csv',[dict(id=r['id'],sid=r['sid'],author=r['author'],GT=c.LABELS[r['y']],**{m:c.LABELS[r['methods'][m]['label']] for m in methods}) for r in rows])
    c.put(folder/'denominators.json',dict(frozen_n=len(allrows),paired_n=len(rows),paired_patients=len(set(r['sid'] for r in rows)),missing_ids=[r['id'] for r in allrows if r not in rows],paired_policy='all formal outputs, including B; Gate missing peer falls backU0'))
    return tables
def main():
    out=c.OUT/'analysis_001';assert not out.exists();blind=c.OUT/'predictions_blind_001';seal=c.read(blind/'manifest.json')
    for name,h in seal['files'].items():assert c.sha(blind/name)==h
    rows=c.lines(blind/'predictions.jsonl');ids={r['id'] for r in rows};import duckdb
    con=duckdb.connect();con.register('permitted',pd.DataFrame({'proposition_id':sorted(ids)}));path=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv'
    gt=dict(con.execute('SELECT t.proposition_id,t.human_gt FROM read_csv(?,all_varchar=true) t JOIN permitted p USING(proposition_id)',[str(path)]).fetchall());assert len(gt)==len(ids);con.close()
    published={}
    for author in ('human','llm'):
        source=c.ROOT/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv'
        for r in c.csvread(source):
            if r['proposition_id'] in ids:published[r['proposition_id']]=c.LABELS.index(r['verdict'])
    assert set(published)==ids
    for r in rows:r['y']=c.LABELS.index(gt[r['id']]);r['methods']['O']=dict(label=published[r['id']])
    out.mkdir();c.put(out/'GT_join.json',dict(created_utc=c.now(),predictions_manifest_sha256=c.sha(blind/'manifest.json'),GT_source_sha256=c.sha(path),GT_join_after_prediction_seal=True))
    table=[]
    for rn in ('R0','R1'):
        rr=[r for r in rows if r['round']==rn]
        if rr:table+=analyze(rn,rr,out/rn);print('036 evaluated',rn,len(rr),flush=True)
    repeat_ids={r['id'] for r in rows if r['round']=='R1'}
    if repeat_ids:table+=analyze('R0_repeat_subset',[r for r in rows if r['round']=='R0' and r['id'] in repeat_ids],out/'R0_repeat_subset')
    c.csvwrite(out/'all_metrics.csv',table);c.jsonl(out/'rows_with_GT.jsonl',rows)
    stability=[];look={(r['round'],r['id']):r for r in rows}
    for m in c.read(c.OUT/'final_freeze_001/config.json')['methods']:
        pairs=[(look['R0',pid],look['R1',pid]) for pid in sorted(repeat_ids)];pairs=[(x,y) for x,y in pairs if x['methods'].get(m,{}).get('label') is not None and y['methods'].get(m,{}).get('label') is not None]
        if pairs:stability.append(dict(method=m,n=len(pairs),label_flips=sum(x['methods'][m]['label']!=y['methods'][m]['label'] for x,y in pairs),correct_R0=sum(x['methods'][m]['label']==x['y'] for x,y in pairs),correct_R1=sum(y['methods'][m]['label']==y['y'] for x,y in pairs)))
    c.csvwrite(out/'repeat_stability.csv',stability);c.put(out/'manifest.json',dict(created_utc=c.now(),files={str(p.relative_to(out)):c.sha(p) for p in out.rglob('*') if p.is_file()}))
if __name__=='__main__':main()
