"""Report both discrete and mixture matched-risk uncertainty at original operating points."""
import numpy as np
import common025 as c
import frontier025_numeric as f
def run():
    rows=c.jl(c.OUT/'preparation_001/rows.jsonl');out={}
    for group in ('024_D','024_Q'):
        rr=[r for r in rows if r['group']==group];pp={r['proposition_id']:r for r in c.csvrows(c.OUT/f'analysis_003/predictions_{group}.csv')};subjects=sorted(set(r['subject_id'] for r in rr));sid=np.array([subjects.index(r['subject_id']) for r in rr]);_,globalpred=f.global_states(rr)
        for method in ('S','SE','SD','SED','peer_U2'):
            pred=[c.LABELS.index(pp[r['proposition_id']][method]) for r in rr];draw=[]
            for seed in range(1000):
                w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects))[sid]
                gr,gf=f.counts(rr,globalpred,w);ar,af=f.counts(rr,pred,w);v=f.matched(gf,gr,af[0],ar[0]);draw.append([v['R_gain_vs_global'],v['R_gain_vs_mixture']])
            ci=np.percentile(draw,[2.5,97.5],axis=0);out[group+'/'+method]=dict(deterministic_ci95=ci[:,0].tolist(),mixture_ci95=ci[:,1].tolist())
    c.write(c.OUT/'interpretation_001/operating_uncertainty.json',out);print(c.canonical(out))
if __name__=='__main__':run()
