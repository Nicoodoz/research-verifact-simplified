"""Patient-isolated OOF; validation selects epoch; no LLM score inputs."""
import os,time,random,argparse,copy
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
from pathlib import Path
import numpy as np
import torch
import common092 as c
from model092 import Verifier
from metrics092 import metrics
class Data:
    def __init__(self):
        self.cfg=c.read(c.TASK/'config.json');root=Path(self.cfg['activation_cache']);assert c.read(c.OUT/'cache_manifest.json')['complete']
        self.rows=c.lines(c.OUT/'cohort.jsonl');self.bags=c.lines(c.OUT/'bags.jsonl');self.windows=c.lines(c.PRIVATE/'windows.jsonl')
        assert [r['id'] for r in self.rows]==[r['id'] for r in self.bags]
        self.x=np.load(root/'lower23.npy',mmap_mode='r');self.cls=np.load(root/'cls24.npy',mmap_mode='r');self.y=np.array([c.LABELS.index(r['GT']) for r in self.rows]);self.features=torch.tensor(np.array(self.cls),device='cuda')
    def hidden(self,ii):
        lens=[len(self.windows[i]['input_ids']) for i in ii];n=max(lens);h=np.zeros((len(ii),n,1024),dtype='float32');mask=np.zeros((len(ii),n),dtype='int64')
        for j,i in enumerate(ii):
            offset=self.windows[i]['offset'];h[j,:lens[j]]=self.x[offset:offset+lens[j]];mask[j,:lens[j]]=1
        return torch.from_numpy(h).cuda(),torch.from_numpy(mask).cuda()
    def forward(self,net,i,adapt):
        ii=self.bags[i]['windows']
        if not adapt:z=self.features[ii]
        else:
            parts=[]
            for lo in range(0,len(ii),self.cfg['window_microbatch']):
                h,mask=self.hidden(ii[lo:lo+self.cfg['window_microbatch']]);parts.append(net.encode(h,mask))
            z=torch.cat(parts)
        return net.head(z.float())
def state_rng():return dict(python=random.getstate(),numpy=np.random.get_state(),torch=torch.get_rng_state(),cuda=torch.cuda.get_rng_state_all())
def restore_rng(r):random.setstate(r['python']);np.random.set_state(r['numpy']);torch.set_rng_state(r['torch'].cpu());torch.cuda.set_rng_state_all([v.cpu() for v in r['cuda']])
def save(path,v):
    temp=path.with_suffix('.tmp');torch.save(v,temp);os.replace(temp,path)
def predict(data,net,ids,adapt):
    net.eval();out=[]
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
        for i in ids:out.append(data.forward(net,i,adapt).float().cpu().numpy())
    return np.array(out)
def probabilities(logits):
    q=np.exp(logits-logits.max(1,keepdims=True));return q/q.sum(1,keepdims=True)
def run_fold(data,fold,adapt):
    cfg=data.cfg;family='finetuned' if adapt else 'frozen';name=f"{family}_fold{fold['fold']}";folder=c.PRIVATE/name;folder.mkdir(exist_ok=True);public=c.OUT/name;public.mkdir(exist_ok=True)
    if (public/'complete.json').exists():
        assert c.read(public/'complete.json')['config_sha256']==c.sha(c.TASK/'config.json');print('reuse',name,flush=True);return
    seed=cfg['seed']+fold['fold'];random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
    train=[i for i,r in enumerate(data.rows) if r['sid'] in fold['train']];valid=[i for i,r in enumerate(data.rows) if r['sid'] in fold['validation']];test=[i for i,r in enumerate(data.rows) if r['sid'] in fold['test']]
    assert set(train).isdisjoint(valid+test) and set(valid).isdisjoint(test)
    net=Verifier(adapt=adapt).cuda();initial={k:v.detach().cpu().clone() for k,v in net.layer.state_dict().items()}
    opt=torch.optim.AdamW([dict(params=net.head.parameters(),lr=cfg['head_lr'])]+([dict(params=net.layer.parameters(),lr=cfg['encoder_lr'])] if adapt else []),weight_decay=cfg['weight_decay'])
    scaler=torch.amp.GradScaler('cuda');start=time.time();epoch=0;cursor=0;order=None;best=None;history=[];elapsed=0.;checkpoint=folder/'resume.pt';steps=0;updates=0;max_grad=0.
    if checkpoint.exists():
        cp=torch.load(checkpoint,map_location='cpu',weights_only=False);assert cp['config_sha256']==c.sha(c.TASK/'config.json')
        net.load_state_dict(cp['net']);opt.load_state_dict(cp['optimizer']);scaler.load_state_dict(cp['scaler']);restore_rng(cp['rng']);epoch=cp['epoch'];cursor=cp['cursor'];order=cp['order'];best=cp['best'];history=cp['history'];elapsed=cp['elapsed'];steps=cp['steps'];updates=cp['updates'];max_grad=cp['max_grad']
    def checkpoint_now():
        save(checkpoint,dict(config_sha256=c.sha(c.TASK/'config.json'),net=net.state_dict(),optimizer=opt.state_dict(),scaler=scaler.state_dict(),rng=state_rng(),epoch=epoch,cursor=cursor,order=order,best=best,history=history,elapsed=elapsed+time.time()-start,steps=steps,updates=updates,max_grad=max_grad))
    while epoch<cfg['epochs']:
        if order is None:order=np.random.permutation(train).tolist();cursor=0
        net.train()
        while cursor<len(order):
            batch=order[cursor:cursor+cfg['effective_batch_claims']];opt.zero_grad(set_to_none=True);loss_sum=0.
            for i in batch:
                with torch.autocast('cuda',dtype=torch.float16):logits=data.forward(net,i,adapt);loss=torch.nn.functional.cross_entropy(logits.unsqueeze(0),torch.tensor([data.y[i]],device='cuda',dtype=torch.long))/len(batch)
                assert torch.isfinite(loss);scaler.scale(loss).backward();loss_sum+=float(loss.detach())
            scaler.unscale_(opt);grad=float(torch.nn.utils.clip_grad_norm_([p for p in net.parameters() if p.requires_grad],1.));max_grad=max(max_grad,grad) if np.isfinite(grad) else max_grad
            old_scale=scaler.get_scale();scaler.step(opt);scaler.update();updates+=int(scaler.get_scale()>=old_scale);steps+=1;cursor+=len(batch)
            if cursor%256<len(batch) or cursor==len(order):
                checkpoint_now();status=dict(model=name,epoch=epoch+1,completed=cursor,total=len(order),seconds=elapsed+time.time()-start,loss=loss_sum,utc=c.now());c.put(c.OUT/'training_progress.json',status);print(status,flush=True)
        vv=predict(data,net,valid,adapt);mm=metrics(data.y[valid],vv.argmax(1),probabilities(vv));key=(mm['MCC'],mm['PA'],mm['Macro_F1'],-mm['false_S']);history.append(dict(epoch=epoch+1,validation=mm))
        if best is None or key>tuple(best['key']):
            best=dict(epoch=epoch+1,key=key);save(folder/'best.pt',net.state_dict())
        print(name,'validation epoch',epoch+1,mm,'best',best['epoch'],flush=True);epoch+=1;cursor=0;order=None;checkpoint_now();c.put(public/'training_history.json',history)
    net.load_state_dict(torch.load(folder/'best.pt',map_location='cuda',weights_only=True));t0=time.time();zz=predict(data,net,test,adapt);seconds_test=time.time()-t0;qq=probabilities(zz)
    predictions=[dict(id=data.rows[i]['id'],sid=data.rows[i]['sid'],fold=fold['fold'],prediction=c.LABELS[int(z.argmax())],logits=z.tolist(),probabilities=q.tolist()) for i,z,q in zip(test,zz,qq)]
    c.jsonl(public/'predictions.jsonl',predictions)
    delta=sum(float((v.detach().cpu()-initial[k]).square().sum()) for k,v in net.layer.state_dict().items())**.5
    # Representation witness on fixed inner-training claim, no test-dependent selection.
    ii=data.bags[train[0]]['windows'][:2];h,mask=data.hidden(ii)
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):changed=net.encode(h,mask).float().cpu().numpy()
    difference=float(np.linalg.norm(changed-np.asarray(data.cls[ii])))
    assert (delta>0 and difference>0 and updates>0) if adapt else delta==0
    c.put(public/'complete.json',dict(family=family,fold=fold['fold'],best=best,train_n=len(train),validation_n=len(valid),test_n=len(test),config_sha256=c.sha(c.TASK/'config.json'),weights_sha256=c.sha(folder/'best.pt'),weights_bytes=(folder/'best.pt').stat().st_size,trainable_parameters=sum(p.numel() for p in net.parameters() if p.requires_grad),encoder_parameter_L2_change=delta,representation_L2_change=difference,witness_id=data.rows[train[0]]['id'],optimizer_steps=steps,non_skipped_updates=updates,max_gradient_norm=max_grad,seconds=elapsed+time.time()-start,test_inference_seconds=seconds_test,peak_GPU_MiB=torch.cuda.max_memory_allocated()/1024**2,GT_not_model_input=True))
    del net,opt;torch.cuda.empty_cache()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--fold',type=int);parser.add_argument('--family',choices=['frozen','finetuned']);args=parser.parse_args();torch.set_num_threads(4);data=Data()
    for f in c.read(c.OUT/'folds.json'):
        if args.fold is not None and f['fold']!=args.fold:continue
        for adapt in [False,True]:
            if args.family and args.family!=('finetuned' if adapt else 'frozen'):continue
            run_fold(data,f,adapt)
if __name__=='__main__':main()
