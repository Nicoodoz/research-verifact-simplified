"""One fixed scalar text-logit fusion and a matched bias-only control."""
import numpy as np
from scipy.special import logsumexp,softmax
from scipy.optimize import minimize
import common092 as c
from analyze092 import table,paired
def baseline_logits(r):
    s=r['scores'];s=[s[k] for k in c.LABELS] if isinstance(s,dict) else s
    z=np.log(np.maximum(np.asarray(s,dtype=float)/100,1e-6))+np.log((np.array([1108,100,170])/1378)/(np.array([48,47,48])/143))
    z[0]+=.1342909508820116
    assert c.LABELS[z.argmax()]==r['label']
    return z
def fit(base,text,y,use_text):
    def objective(p):
        bias=np.array([p[0],p[1],-p[0]-p[1]]);z=base+bias+(p[2]*text if use_text else 0);q=softmax(z,axis=1);loss=np.mean(logsumexp(z,axis=1)-z[np.arange(len(y)),y])+.01*(p@p)
        q[np.arange(len(y)),y]-=1;g=[np.mean(q[:,0]-q[:,2]),np.mean(q[:,1]-q[:,2])]
        if use_text:g.append(np.mean(np.sum(q*text,axis=1)))
        return loss,np.asarray(g)+.02*p
    opt=minimize(objective,np.zeros(3 if use_text else 2),jac=True,method='L-BFGS-B',bounds=[(-5,5),(-5,5)]+([(0,4)] if use_text else []),options={'maxiter':1000,'ftol':1e-12,'gtol':1e-8})
    assert opt.success and np.isfinite(opt.fun),str(opt.message)
    return dict(parameters=opt.x.tolist(),objective=float(opt.fun),iterations=int(opt.nit),success=True)
def decode(z,t,fit,use_text):
    p=fit['parameters'];v=z+np.array([p[0],p[1],-p[0]-p[1]])+(p[2]*t if use_text else 0)
    return c.LABELS[int(v.argmax())]
def main():
    assert c.read(c.OUT/'fusion_decision.json')['run_fusion'] is True
    rows={r['id']:r for r in c.lines(c.OUT/'oof_predictions.jsonl')};baseline={r['id']:r for r in c.lines(c.OUT/'cached_baselines.jsonl') if r['arm']=='B'};out=[];models=[]
    for f in c.read(c.OUT/'folds.json'):
        data=np.load(c.PRIVATE/f"fusion_train_fold{f['fold']}.npz",allow_pickle=False);ids=data['ids'].tolist()
        assert all(rows[p]['sid'] in f['train'] for p in ids)
        text=data['logits'].astype(float);text-=text.mean(1,keepdims=True);z=np.array([baseline_logits(baseline[p]) for p in ids]);y=np.array([c.LABELS.index(rows[p]['GT']) for p in ids])
        fits={name:fit(z,text,y,use) for name,use in [('bias_only',False),('text_fusion',True)]};models.append(dict(fold=f['fold'],training_ids=ids,training_patients=sorted({rows[p]['sid'] for p in ids}),fits=fits,text_weights_sha256=str(data['weights_sha256']),outer_patients=f['test']))
        test=c.lines(c.OUT/f"finetuned_fold{f['fold']}"/'predictions.jsonl')
        for r in test:
            if r['id'] not in baseline:continue
            source=rows[r['id']];a=baseline[r['id']];x=dict(source,predictions=dict(source['predictions']));x['fusion_baseline_valid']=a['valid']
            if a['valid']:
                zz=baseline_logits(a);t=np.asarray(r['logits']);t-=t.mean()
                for name,use in [('bias_only',False),('text_fusion',True)]:x['predictions'][name]=decode(zz,t,fits[name],use)
            else:
                for name in fits:x['predictions'][name]=a['label']
            out.append(x)
    out.sort(key=lambda r:r['id']);assert len(out)==len(baseline)==len({r['id'] for r in out})
    c.jsonl(c.OUT/'fusion_predictions.jsonl',out);c.put(c.OUT/'fusion_models.json',models)
    result=dict(metrics=table(out,['Original','B','finetuned','bias_only','text_fusion']),paired_vs_B=paired(out,'B','text_fusion'),paired_vs_bias=paired(out,'bias_only','text_fusion'),invalid_B_preserved=sum(not r['fusion_baseline_valid'] for r in out),selection_note='Conditional exploratory extension; train text logits in-sample, all outer patients excluded from representation/epoch/fusion training; no hyperparameter search.')
    c.put(c.OUT/'fusion_results.json',result);print(result['metrics'])
if __name__=='__main__':main()
