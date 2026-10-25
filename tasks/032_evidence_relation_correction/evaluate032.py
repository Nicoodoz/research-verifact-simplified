"""Confirmation is scored only after all trained predictions are frozen."""
import json,numpy as np
import common032 as c
from verifact_research.evaluation import paired_compare

def run():
    c.block_network();folder=c.OUT/'inference_001';mf=c.read(folder/'manifest.json')
    c.require(c.sha(folder/'predictions_blind.jsonl')==mf['predictions_sha256'],'Blind predictions modified')
    rr=c.lines(folder/'predictions_blind.jsonl');out=c.OUT/'analysis_001';out.mkdir(exist_ok=True)
    c.require(set(mf['training_patients']).isdisjoint(mf['confirmation_patients']),'Patient overlap')
    gt=c.scoped_gt([r['proposition_id'] for r in rr]);rows=[dict(r,human_gt=gt[r['proposition_id']]) for r in rr]
    c.put(out/'GT_connection.json',dict(created_utc=c.now(),prediction_manifest_sha256=c.sha(folder/'manifest.json'),n=len(rows),scope='031 confirmation12 exposed development'))
    methods=list(rr[0]['predictions']);pred={m:np.array([r['predictions'][m] for r in rr]) for m in methods};truth=np.array([c.LABELS.index(r['human_gt']) for r in rows]);base=pred['U2'];metrics={};table=[];transitions=[];patients=[]
    scopes={'all':list(range(len(rows)))}
    for author in sorted({r['author_type'] for r in rows}):scopes[author]=[i for i,r in enumerate(rows) if r['author_type']==author]
    for scope,idx in scopes.items():
        sub=[rows[i] for i in idx]
        for m,p in pred.items():
            v=c.metric(sub,p[idx]);metrics[scope+'/'+m]=v
            table.append(dict(scope=scope,method=m,**{k:v[k] for k in ['n','correct','PA','MCC','AC1','false_S']}))
    for m,p in pred.items():
        for i,r in enumerate(rows):
            if p[i]!=base[i]:transitions.append(dict(method=m,proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],old_candidate=r['candidate'],GT=c.LABELS[truth[i]],U2=c.LABELS[base[i]],new=c.LABELS[p[i]],fix=int(base[i]!=truth[i] and p[i]==truth[i]),harm=int(base[i]==truth[i] and p[i]!=truth[i])))
        for sid in sorted({r['subject_id'] for r in rows}):
            ii=[i for i,r in enumerate(rows) if r['subject_id']==sid];v=c.metric([rows[i] for i in ii],p[ii]);patients.append(dict(method=m,subject_id=sid,**{k:v[k] for k in ['n','correct','PA','MCC','false_S']},net_vs_U2=int(sum(p[ii]==truth[ii])-sum(base[ii]==truth[ii]))))
    pairs={};make=lambda pp:[dict(proposition_id=r['proposition_id'],verdict=c.LABELS[int(v)]) for r,v in zip(rows,pp)]
    comparisons=[(m,'U2') for m in methods if m not in ['U0','U2']]+[('attention',m) for m in ['score','fixed','attention_single','attention_no_lambda','attention_candidate_only','SD_A']]
    for new,old in comparisons:pairs[new+'__vs__'+old]=paired_compare(rows,make(pred[old]),make(pred[new]),iterations=1000)
    c.put(out/'metrics.json',metrics);c.csvwrite(out/'metrics.csv',table);c.put(out/'paired.json',pairs);c.csvwrite(out/'transitions.csv',transitions);c.csvwrite(out/'patients.csv',patients)
    changes={}
    oldcand=np.array([r['candidate'] for r in rows])
    for m,p in pred.items():
        changes[m]=dict(fixes=int(sum((base!=truth)&(p==truth))),harms=int(sum((base==truth)&(p!=truth))),candidate_fixes=int(sum(oldcand&(base!=truth)&(p==truth))),noncandidate_fixes=int(sum(~oldcand&(base!=truth)&(p==truth))),candidate_harms=int(sum(oldcand&(base==truth)&(p!=truth))),noncandidate_harms=int(sum(~oldcand&(base==truth)&(p!=truth))),new_false_S=int(sum((truth!=0)&(base!=0)&(p==0))),prevented_false_S=int(sum((truth!=0)&(base==0)&(p!=0))),old_candidate_R_retained=int(sum(oldcand&(truth==0)&(p==0))))
    c.put(out/'changes.json',changes)
    expected=c.read(c.ROOT/'outputs/031_training_expansion_confirmation/analysis_001/metrics.json')
    checks={}
    for m,old in [('U0','U0'),('U2','U2'),('SD_A','after_A')]:
        for k in ['n','correct','PA','MCC','AC1','false_S']:
            ok=abs(metrics['all/'+m][k]-expected['all/'+old][k])<1e-10;checks[m+'/'+k]=bool(ok);c.require(ok,'031 baseline re-evaluation mismatch')
    c.put(out/'baseline_checks.json',checks);c.put(out/'manifest.json',dict(created_utc=c.now(),n=len(rows),patient_bootstrap='1000 paired patient draws; frozen predictions, no refitting',files={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}))
    c.state('evaluated',state='ready',n=len(rows));print('Confirmation evaluation complete',flush=True)
if __name__=='__main__':run()
