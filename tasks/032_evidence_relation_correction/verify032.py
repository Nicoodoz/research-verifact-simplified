"""Read-only saved-model replay; no refitting or network. Execution self-check."""
import argparse
import numpy as np
import torch
import common032 as c
import learning032 as l

def run(name):
    c.block_network();out=c.OUT/name;c.require(not out.exists(),'Verification output must be new')
    rows,data=l.load_arrays();test=np.array([i for i,r in enumerate(rows) if r['split']=='confirmation']);train_ids={r['proposition_id'] for r in rows if r['split']=='train'}
    cfg=c.read(c.OUT/'preparation_001/config.json');selections=c.read(c.OUT/'training_001/selections.json');checks={};replayed={}
    stored=c.lines(c.OUT/'inference_001/predictions_blind.jsonl');c.require([r['proposition_id'] for r in stored]==[rows[i]['proposition_id'] for i in test],'Confirmation order')
    for family,v in selections.items():
        outputs=[]
        for seed in cfg['training_seeds']:
            folder=c.OUT/'inference_001/models'/f'{family}_s{seed}';meta=c.read(folder/'model.json');checks[family+str(seed)+'_train']=set(meta['training_ids'])==train_ids
            checks[family+str(seed)+'_weights']=c.sha(folder/'weights.pt')==meta['weights_sha256']
            model=l.Head(family,v['hidden'],cfg['residual_bound']);model.load_state_dict(torch.load(folder/'weights.pt',map_location='cpu',weights_only=True));model.eval()
            stats={k:np.array(z,dtype='float32') for k,z in meta['statistics'].items()};outputs.append(l.predict(model,stats,data,test))
        z=l.base_logits(data,test,family)+v['scale']*np.mean(outputs,axis=0);replayed[family]=l.decode(z)
        old=np.load(c.OUT/'inference_001'/f'{family}_logits.npz')['logits'];checks[family+'_logits']=bool(np.allclose(z,old,rtol=1e-6,atol=1e-7));checks[family+'_labels']=bool(np.array_equal(replayed[family],[r['predictions'][family] for r in stored]))
    restricted=np.array([replayed['attention'][j] if rows[i]['candidate'] else rows[i]['u2'] for j,i in enumerate(test)])
    checks['candidate_restriction']=bool(np.array_equal(restricted,[r['predictions']['attention_candidate_only'] for r in stored]))
    c.require(all(checks.values()),'Saved model replay failed');out.mkdir();c.put(out/'checks.json',dict(created_utc=c.now(),passed=True,checks=checks,new_fits=0,API_calls=0,independent_audit=False));print('Saved model replay passed',len(checks),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='verification_001');run(p.parse_args().output)
