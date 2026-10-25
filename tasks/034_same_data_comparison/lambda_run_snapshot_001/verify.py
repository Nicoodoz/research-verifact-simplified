"""Verify stored fits, predictions, original anchors and source fingerprints."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import common as c
import learning as l
import analysis as a

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--run',required=True);args=ap.parse_args();out=Path(args.run).resolve()
    freeze=c.read(out/'freeze.json');checks=[]
    def require(ok,name):
        if not ok:raise AssertionError(name)
        checks.append(name)
    for rel,h in {**freeze['sources'],**freeze['code']}.items():require(c.sha(c.ROOT/rel)==h,'hash:'+rel)
    for rel,h in c.read(out/'manifest.json').items():require(c.sha(out/rel)==h,'output:'+rel)
    datasets,folds,_=c.load_data();mapping={'DS_to_Q':'bridge_qwen','Q_to_DS':'bridge_deepseek'}
    for p in sorted((out/'fits').glob('*/fold?.json')):
        record=c.read(p);source=datasets[record['source']];train=[r for r in source if r['fold']!=record['fold']]
        require(record['training_ids']==[r['id'] for r in train],'train IDs:'+str(p))
        digest=hashlib.sha256(json.dumps([(r['id'],r['y']) for r in train]).encode()).hexdigest()
        require(record['training_label_sha256']==digest,'train labels:'+str(p))
        for name,description in record['evaluation'].items():
            rr=datasets[mapping.get(name,name)];ii=np.array([i for i,r in enumerate(rr) if r['fold']==record['fold']]);held=[rr[i] for i in ii]
            require(set(record['training_patients']).isdisjoint(r['sid'] for r in held),'patient isolation:'+name+str(record['fold']))
            actual=l.infer(held,record['models']);saved=np.load(out/'frozen_predictions'/(name+'.npz'))
            for method,(labels,lp) in actual.items():
                require(np.array_equal(labels,saved[method+'_labels'][ii]),'labels:'+name+method+str(record['fold']))
                require(np.allclose(lp,saved[method+'_logprob'][ii],atol=1e-12,rtol=0),'logprob:'+name+method+str(record['fold']))
        rebuilt,table=l.fit_all(train)
        require(rebuilt==record['models'],'deterministic parameter refit:'+str(p))
        saved_states=c.csvread(p.with_name(p.stem+'_states.csv'))
        require(len(table)==len(saved_states),'selection state count:'+str(p))
    names=c.read(out/'completion.json')['datasets']
    for name in names:
        rr=datasets[mapping.get(name,name)];saved=np.load(out/'frozen_predictions'/(name+'.npz'));metrics=c.read(out/name/'metrics.json')
        for scope in ('all','human','llm'):
            ii=np.array([i for i,r in enumerate(rr) if scope=='all' or r['author']==scope]);selected=[rr[i] for i in ii]
            for m in c.METHODS:
                actual=a.point(selected,saved[m+'_labels'][ii],saved[m+'_logprob'][ii])
                require(actual==metrics[scope+'/'+m],'metrics:'+name+scope+m)
        require(np.array_equal(saved['U2_labels'],saved['U2_T_labels']),'U2 temperature label invariance:'+name)
    old=c.jsonl(c.ROOT/'outputs/022_competition_aware_support_calibration/stageA_002/oof_predictions.jsonl')
    methods={'U0':'U0','U2':'U2','G':'G_022','M':'M_022','V':'V_022','T':'T_022'}
    oldmap={(r['proposition_id'],r['repeat'],r['method']):r['verdict'] for r in old}
    matched=0
    for rep in (0,1):
        name='old_R'+str(rep);rr=datasets[name];saved=np.load(out/'frozen_predictions'/(name+'.npz'))
        for oldmethod,newmethod in methods.items():
            expected=[oldmap[(r['id'],rep,oldmethod)] for r in rr]
            actual=[c.LABELS[i] for i in saved[newmethod+'_labels']]
            require(actual==expected,'022 exact labels:'+name+newmethod);matched+=len(rr)
    c.put(out/'verification.json',dict(status='PASS',checks_passed=len(checks),legacy_labels_checked=matched,
      refitted_cv_groups=16,independent_audit=False,checks=checks,verified_utc=c.now()))
    print('Verification PASS',len(checks),'checks;',matched,'legacy labels')

if __name__=='__main__':main()
