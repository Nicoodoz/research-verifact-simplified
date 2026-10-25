"""Conditional only: train features from this fold's own model, never other-fold OOF."""
import time
import numpy as np
import torch
import common092 as c
from train092 import Data,predict
from model092 import Verifier
def main():
    assert c.read(c.OUT/'fusion_decision.json')['run_fusion'] is True
    torch.set_num_threads(4);data=Data();baselines={(r['id'],r['arm']):r for r in c.lines(c.OUT/'cached_baselines.jsonl')};log=[];bridge=[]
    assert c.read(c.OUT/'cloud_training_manifest.json')['bags_semantically_identical_to_local_pretraining']
    for f in c.read(c.OUT/'folds.json'):
        dest=c.PRIVATE/f"fusion_train_fold{f['fold']}.npz"
        ids=[i for i,r in enumerate(data.rows) if r['sid'] in f['train'] and (r['id'],'B') in baselines and baselines[r['id'],'B']['valid']]
        assert ids and not {data.rows[i]['sid'] for i in ids}&set(f['test']+f['validation'])
        weights=c.PRIVATE/f"finetuned_fold{f['fold']}"/'best.pt'
        assert c.sha(weights)==c.read(c.OUT/f"finetuned_fold{f['fold']}"/'complete.json')['weights_sha256']
        if dest.exists():
            saved=np.load(dest,allow_pickle=False);assert saved['ids'].tolist()==[data.rows[i]['id'] for i in ids]
            continue
        net=Verifier(adapt=False).cuda().eval();net.load_state_dict(torch.load(weights,map_location='cuda',weights_only=True));t=time.time();logits=predict(data,net,ids,True)
        np.savez(dest,ids=np.array([data.rows[i]['id'] for i in ids]),logits=logits,weights_sha256=np.array(c.sha(weights)))
        log.append(dict(fold=f['fold'],N=len(ids),patients=len({data.rows[i]['sid'] for i in ids}),seconds=time.time()-t,weights_sha256=c.sha(weights),in_sample_training_features=True,cache='original RTX3060 lower23 cache, not transferred RTX4090 cache'))
        test_ids=[i for i,r in enumerate(data.rows) if r['sid'] in f['test'] and (r['id'],'B') in baselines]
        local=predict(data,net,test_ids,True)
        cloud={r['id']:r for r in c.lines(c.OUT/f"finetuned_fold{f['fold']}"/'predictions.jsonl')}
        old=np.array([cloud[data.rows[i]['id']]['logits'] for i in test_ids])
        bridge.append(dict(fold=f['fold'],N=len(test_ids),max_abs_logit_difference=float(np.abs(local-old).max()),mean_abs_logit_difference=float(np.abs(local-old).mean()),label_disagreements=int((local.argmax(1)!=old.argmax(1)).sum()),disagreement_ids=[data.rows[i]['id'] for i,a,b in zip(test_ids,local.argmax(1),old.argmax(1)) if a!=b],note='No GT used; original cloud predictions retained for final evaluation. This measures hardware/cache numerical drift, not repeat training stability.'))
        del net;torch.cuda.empty_cache()
    c.put(c.OUT/'fusion_feature_cost.json',log)
    c.put(c.OUT/'local_cloud_numerical_bridge.json',bridge)
if __name__=='__main__':main()
