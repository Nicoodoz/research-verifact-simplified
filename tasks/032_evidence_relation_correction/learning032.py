"""Small residual heads; all statistics are fitted on training patients only."""
import random
import numpy as np
import torch
from torch import nn
import common032 as c

def decode(z):return np.where(z[:,0]>np.maximum(z[:,1],z[:,2]),0,np.where(z[:,1]>=z[:,2],1,2))
class Head(nn.Module):
    def __init__(self,family,hidden,bound):
        super().__init__();self.family=family;self.bound=bound;self.views=1 if family=='attention_single' else 2
        if family.startswith('attention'):
            self.encoder=nn.Sequential(nn.Linear(40,hidden),nn.Tanh());self.attention=nn.Linear(hidden,2)
            size=6+self.views*2*hidden
        elif family=='fixed':size=6+4*40
        else:size=6
        self.head=nn.Sequential(nn.Linear(size,hidden),nn.Tanh(),nn.Linear(hidden,3))
        nn.init.zeros_(self.head[-1].weight);nn.init.zeros_(self.head[-1].bias)
    def forward(self,s,x,mask,kind):
        pooled=[]
        if self.family!='score':
            h=self.encoder(x) if self.family.startswith('attention') else x
            for view in range(self.views):
                m=mask & (kind==view);empty=~m.any(dim=1);m=m.clone();m[empty]=mask[empty] & (kind[empty]==0)
                if self.family.startswith('attention'):
                    weights=self.attention(h).masked_fill(~m.unsqueeze(-1),-1e9).softmax(dim=1)
                    pooled.append(torch.einsum('bnh,bnk->bkh',h,weights).flatten(1))
                else:
                    pooled.extend([(h*m.unsqueeze(-1)).sum(1)/m.sum(1).clamp_min(1).unsqueeze(-1),h.masked_fill(~m.unsqueeze(-1),-1e9).max(1).values])
        v=torch.cat([s]+pooled,dim=1);return self.bound*torch.tanh(self.head(v)/self.bound)
def load_arrays():
    rows=c.lines(c.OUT/'preparation_001/inputs_blind.jsonl');d=np.load(c.CACHE/'bags.npz')
    c.require(list(d['ids'])==[r['proposition_id'] for r in rows],'Feature order mismatch')
    p=np.array([r['scores'] for r in rows],dtype='float64')/100;z=np.log(np.maximum(p,1e-6));s=np.concatenate([p,z],axis=1).astype('float32')
    c.require(np.array_equal(decode(z),[r['u0'] for r in rows]),'U0 precision mismatch')
    z2=z.copy();z2[:,0]+=2;c.require(np.array_equal(decode(z2),[r['u2'] for r in rows]),'U2 precision mismatch')
    return rows,dict(s=s,x=d['x'],mask=d['mask'],kind=d['x'][:,:,38].astype('int64'),z=z)

def statistics(data,ids):
    s=data['s'][ids];v=data['x'][ids][data['mask'][ids]]
    return dict(smean=s.mean(0),sscale=np.maximum(s.std(0),1e-4),xmean=v.mean(0),xscale=np.maximum(v.std(0),1e-4))
def tensors(data,ids,stats):
    s=np.clip((data['s'][ids]-stats['smean'])/stats['sscale'],-8,8)
    x=np.clip((data['x'][ids]-stats['xmean'])/stats['xscale'],-8,8)
    return [torch.from_numpy(a) for a in [s.astype('float32'),x.astype('float32'),data['mask'][ids],data['kind'][ids]]]
def fit(data,ids,y,family,hidden,seed,cfg):
    torch.set_num_threads(4);random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    stats=statistics(data,ids);net=Head(family,hidden,cfg['residual_bound']);tx=tensors(data,ids,stats)
    z=data['z'][ids].copy();z[:,0]+=0 if family=='attention_no_lambda' else 2
    base=torch.from_numpy(z).float();target=torch.from_numpy(y[ids]).long();c.require(bool((target>=0).all()),'Confirmation GT passed into fit')
    opt=torch.optim.AdamW(net.parameters(),lr=cfg['learning_rate'],weight_decay=cfg['weight_decay']);losses=[]
    for epoch in range(cfg['epochs']):
        opt.zero_grad();delta=net(*tx);loss=nn.functional.cross_entropy(base+delta,target)+cfg['residual_penalty']*delta.square().mean()
        c.require(bool(torch.isfinite(loss)),'Nonfinite training loss');loss.backward();torch.nn.utils.clip_grad_norm_(net.parameters(),5);opt.step()
        if epoch%10==0 or epoch==cfg['epochs']-1:losses.append(dict(epoch=epoch+1,loss=float(loss.detach())))
    return net.eval(),stats,losses
def predict(net,stats,data,ids):
    output=[]
    with torch.inference_mode():
        for start in range(0,len(ids),128):output.append(net(*tensors(data,ids[start:start+128],stats)).numpy())
    return np.concatenate(output,axis=0) if output else np.empty((0,3),dtype='float32')
def serial_stats(stats):return {k:v.tolist() for k,v in stats.items()}
def fitted(data,ids,y,family,hidden,seed,cfg,path,rows):
    path.mkdir(parents=True,exist_ok=True);mp=path/'model.json';wp=path/'weights.pt'
    expected=dict(training_ids=[rows[i]['proposition_id'] for i in ids],family=family,hidden=hidden,seed=seed,config_hash=c.digest(cfg))
    if mp.exists() and wp.exists():
        meta=c.read(mp)
        for k,v in expected.items():c.require(meta[k]==v,'Saved model binding mismatch: '+k)
        net=Head(family,hidden,cfg['residual_bound']);net.load_state_dict(torch.load(wp,map_location='cpu',weights_only=True));stats={k:np.asarray(v,dtype='float32') for k,v in meta['statistics'].items()};return net.eval(),stats
    net,stats,losses=fit(data,ids,y,family,hidden,seed,cfg);torch.save(net.state_dict(),wp)
    c.put(mp,dict(**expected,training_patients=sorted({rows[i]['subject_id'] for i in ids}),statistics=serial_stats(stats),losses=losses,weights_sha256=c.sha(wp)))
    return net,stats

def base_logits(data,ids,family):
    z=data['z'][ids].copy();z[:,0]+=0 if family=='attention_no_lambda' else 2;return z
