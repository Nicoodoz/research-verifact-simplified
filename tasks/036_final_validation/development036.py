"""Complete the predefined 022 controls on precisely the 035 frozen folds."""
import sys
import numpy as np
import common036 as c
sys.path.insert(0,str(c.ROOT/'tasks/035_lambda_boundary_calibration'))
import common as old
import learning as l
import analysis as a
sys.path.insert(0,str(c.ROOT/'tasks/022_competition_aware_support_calibration'))
import calibration022 as cal

def main():
    out=c.OUT/'development_001';c.require(not out.exists(),'Do not overwrite development');out.mkdir(parents=True)
    source=c.ROOT/'outputs/035_lambda_boundary_calibration/run_002'
    data=c.read(source/'inputs_numeric.json');tables=[];checks=[];files=[source/'inputs_numeric.json',source/'full_development_models.json']
    jobs=[('old_R0',{'old_R0':data['old_R0'],'old_R1':data['old_R1']}),('main40',{'main40':data['main40']}),('bridge_deepseek',{'bridge_deepseek':data['bridge_deepseek'],'DS_to_Q':data['bridge_qwen']}),('bridge_qwen',{'bridge_qwen':data['bridge_qwen'],'Q_to_DS':data['bridge_deepseek']})]
    for src,targets in jobs:
        output={name:{} for name in targets}
        for name,rows in targets.items():
            path=source/'frozen_predictions'/f'{name}.npz';files.append(path);f=np.load(path,allow_pickle=False)
            output[name]={m:(f[m+'_labels'],f[m+'_logprob']) for m in old.METHODS}
            for kind in 'TGMV':output[name]['Std_'+kind]=(np.full(len(rows),-1,int),np.full((len(rows),3),np.nan))
            z,_=old.arrays(rows);z[:,0]+=4;output[name]['U4']=(old.decode(z),l.logprob(z))
        for fold in range(4):
            train=[r for r in data[src] if r['fold']!=fold];z,y=old.arrays(train);fits={k:cal.fit(z,y,k) for k in 'TGMV'}
            c.put(out/'fits'/src/f'fold{fold}.json',dict(models=fits,training_patients=sorted(set(r['sid'] for r in train)),training_ids=[r['id'] for r in train]))
            for name,rows in targets.items():
                ii=np.array([i for i,r in enumerate(rows) if r['fold']==fold]);held=[rows[i] for i in ii]
                assert set(r['sid'] for r in train).isdisjoint(r['sid'] for r in held)
                zz,_=old.arrays(held)
                for k,fit in fits.items():
                    v=cal.transform(zz,k,fit['theta']);output[name]['Std_'+k][0][ii]=cal.labels(v);output[name]['Std_'+k][1][ii]=l.logprob(v)
        for name,rows in targets.items():
            pp=output[name];assert all(np.all(p>=0) and np.isfinite(lp).all() for p,lp in pp.values())
            tables.extend(a.analyze(name,rows,pp,out))
            checks.append(dict(dataset=name,n=len(rows),Joint_vs_U4_label_flips=int(np.sum(pp['Joint_NLL'][0]!=pp['U4'][0])),temperature_vs_U0_flips=int(np.sum(pp['Std_T'][0]!=pp['U0'][0]))))
            np.savez_compressed(out/name/'frozen_predictions.npz',**{m+'_'+k:v[j] for m,v in pp.items() for j,k in enumerate(['labels','logprob'])})
            print('036 development',name,flush=True)
    z,y=old.arrays(data['main40']);full={k:cal.fit(z,y,k) for k in 'TGMV'}
    c.put(out/'standard_full_development_models.json',dict(models=full,training_ids=[r['id'] for r in data['main40']]))
    c.csvwrite(out/'all_metrics.csv',tables);c.csvwrite(out/'U4_Joint_check.csv',checks)
    c.put(out/'manifest.json',dict(created_utc=c.now(),sources={str(p.relative_to(c.ROOT)):c.sha(p) for p in files},files={str(p.relative_to(out)):c.sha(p) for p in out.rglob('*') if p.is_file()}))
    print('036 development controls complete',flush=True)
if __name__=='__main__':main()
