"""Seal every final prediction BEFORE joining reserved physician labels."""
import sys
import numpy as np
from scipy.special import expit
import common036 as c
import api036 as a
from numerics036 import old,l,cal

def infer_scores(scores,models,standard):
    z=np.log(np.maximum(np.array([[scores[k]/100 for k in c.LABELS]],float),1e-6));out={}
    for name,m in models.items():
        if m['kind']=='joint':v=z*m['a'];v=v.copy();v[:,0]+=m['b']
        else:v=z.copy();v[:,0]+=m['lam'];v*=m['beta']
        out[name]=dict(label=int(old.decode(v)[0]),logprob=l.logprob(v)[0].tolist())
    for kind,m in standard.items():
        v=cal.transform(z,kind,m['theta']);out['Std_'+kind]=dict(label=int(cal.labels(v)[0]),logprob=l.logprob(v)[0].tolist())
    v=z.copy();v[:,0]+=4;out['U4']=dict(label=int(old.decode(v)[0]),logprob=l.logprob(v)[0].tolist())
    assert out['U2']['label']==out['U2_T']['label']
    return out
def gate(model,features):
    m=model['final_fit'];assert not m['fallback']
    x=np.array([features[k] for k in m['features']]);p=float(expit(((x-np.array(m['mean']))/np.array(m['scale']))@np.array(m['coef'])+m['intercept']))
    return dict(probability=p,threshold=model['threshold'],keep=p>=model['threshold'])
def main():
    out=c.OUT/'predictions_blind_001';assert not out.exists()
    import execute036 as execute
    execute.verify_freeze();attempts,terminal,_=a.state();counts={}
    for x in attempts:counts[x['request_id']]=counts.get(x['request_id'],0)+1
    jobs=c.lines(c.OUT/'judge_inputs_001/jobs.jsonl')+c.lines(c.OUT/'candidate_freeze_001/jobs.jsonl')
    assert all(j['request_id'] in terminal or counts.get(j['request_id'],0)>=3 for j in jobs),'Pending requested outputs'
    f=c.OUT/'final_freeze_001';models=c.read(f/'models035.json')['models'];standard=c.read(f/'standard_models022.json')['models'];model=c.read(f/'gate_A.json')
    mat={r['proposition_id']:r for r in c.lines(c.OUT/'judge_inputs_001/materials.jsonl')};rows=[];normalized=[]
    for j in jobs:
        t=terminal.get(j['request_id']);p=t['parsed'] if t else dict(status='missing')
        normalized.append(dict(request_id=j['request_id'],round=j['round'],role=j['role'],proposition_id=j['proposition_id'],parsed=p,receipt=t['receipt'] if t else None))
        if j['role']!='score':continue
        pid=j['proposition_id'];round_name=j['round'];m=mat[pid];get=lambda role:terminal.get('036_'+round_name+'_'+role+'_'+pid,{}).get('parsed',dict(status='missing'))
        b=get('baseline');q=get('peer');valid=p['status'] in a.api.VALID
        result={};features=None;g=None;candidate=False
        if valid:
            result=infer_scores(p['scores'],models,standard);u0=result['U0']['label'];u2=result['U2']['label'];candidate=u0!=0 and u2==0
            result['Score_verdict']=dict(label=c.LABELS.index(p['verdict']))
            if candidate and q['status'] in a.api.VALID:
                features=c.base.score_features(p['scores'],q['scores']);g=gate(model,features)
                result['Gate_A']=dict(label=0 if g['keep'] else u0,status='gate')
            else:result['Gate_A']=dict(label=u0,status='missing_peer_fallback_U0' if candidate else 'noncandidate_U0')
        result['B']=dict(label=c.LABELS.index(b['verdict']) if b['status'] in a.api.VALID else None)
        rows.append(dict(id=pid,sid=m['subject_id'],author=m['author_type'],round=round_name,reference_sha256=m['reference_sha256'],scores=p.get('scores'),peer_scores=q.get('scores'),candidate=candidate,features=features,gate=g,methods=result,status=dict(score=p['status'],baseline=b['status'],peer=q['status'] if candidate else 'not_required')))
    c.jsonl(out/'predictions.jsonl',rows);c.jsonl(out/'normalized.jsonl',normalized)
    c.csvwrite(out/'cost_ledger.csv',[{k:v for k,v in x.items() if k!='job'} for x in attempts])
    c.put(out/'manifest.json',dict(created_utc=c.now(),reserved_GT_connected=False,rows=len(rows),round_counts={rn:sum(x['round']==rn for x in rows) for rn in ('R0','R1')},files={p.name:c.sha(p) for p in out.iterdir() if p.is_file()},final_configuration_sha256=c.sha(f/'manifest.json'),candidate_manifest_sha256=c.sha(c.OUT/'candidate_freeze_001/manifest.json'),used_or_reserved_cny=sum(x['charge_cny'] for x in attempts)))
    print('036 predictions sealed, no physician GT joined:',len(rows),flush=True)
if __name__=='__main__':main()
