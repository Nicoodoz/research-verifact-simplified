"""Numerical split/gradient witness before any performance-based model selection."""
import os,time
os.environ['HF_HUB_OFFLINE']='1'
import torch,numpy as np
from transformers import AutoTokenizer,AutoModel
import common092 as c
from model092 import Verifier
def main():
    torch.set_num_threads(4);torch.manual_seed(92);start=time.time();path=c.ROOT/'.local_models/032/deberta_v3_nli'
    asset=c.read(c.ROOT/'outputs/032_evidence_relation_correction/model_manifest.json')
    for name,entry in asset['files'].items():assert c.sha(path/name)==entry['sha256'],name
    tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
    batch=tok(['A synthetic patient has a recorded temperature of 37 degrees.','A synthetic note records a planned procedure.'],['The temperature was recorded.','The procedure was completed.'],padding=True,return_tensors='pt').to('cuda')
    base=AutoModel.from_pretrained(path,local_files_only=True,torch_dtype=torch.float16).cuda().eval()
    benchmark=[];cache_batch=2
    for size in [2,4,8]:
        try:
            bb=tok(['Synthetic context. '*180]*size,['A synthetic proposition.']*size,padding='max_length',truncation=True,max_length=512,return_tensors='pt').to('cuda');torch.cuda.reset_peak_memory_stats();t=time.time()
            with torch.inference_mode():oo=base(**bb,output_hidden_states=True)
            torch.cuda.synchronize();peak=torch.cuda.max_memory_allocated()/1024**2;benchmark.append(dict(batch=size,seconds=time.time()-t,peak_MiB=peak))
            if peak<3400:cache_batch=size
            del oo,bb;torch.cuda.empty_cache()
        except torch.cuda.OutOfMemoryError:
            benchmark.append(dict(batch=size,OOM=True));torch.cuda.empty_cache();break
    with torch.inference_mode():out=base(**batch,output_hidden_states=True);h=out.hidden_states[-2].detach().clone();original=out.last_hidden_state[:,0].float().detach().clone();relative=base.encoder.get_rel_embedding().detach().cpu().float()
    torch.save(dict(layer={k:v.detach().cpu().float() for k,v in base.encoder.layer[-1].state_dict().items()},relative=relative),c.PRIVATE/'pretrained_top.pt');del base,out;torch.cuda.empty_cache()
    net=Verifier(adapt=True).cuda().eval();before={k:v.detach().cpu().clone() for k,v in net.layer.state_dict().items()}
    # Clone outside inference_mode so normal backward can save these tensors.
    h=h.clone().float()
    with torch.no_grad(),torch.autocast('cuda',dtype=torch.float16):a=net.encode(h,batch['attention_mask']).float();delta=float((a-original).abs().max())
    assert delta<.05,('Split not numerically equivalent',delta)
    opt=torch.optim.AdamW(net.parameters(),lr=2e-5);scaler=torch.amp.GradScaler('cuda')
    for step in range(8):
        opt.zero_grad()
        with torch.autocast('cuda',dtype=torch.float16):z=net.head(net.encode(h,batch['attention_mask']).float());loss=torch.nn.functional.cross_entropy(z[None],torch.tensor([1],device='cuda'))
        scaler.scale(loss).backward();scaler.unscale_(opt);grad=float(torch.nn.utils.clip_grad_norm_(net.parameters(),1.));scaler.step(opt);scaler.update()
    weight_delta=sum(float((v.detach().cpu()-before[k]).square().sum()) for k,v in net.layer.state_dict().items())**.5
    with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):after=net.encode(h,batch['attention_mask']).float();representation_delta=float((after-a).norm())
    assert weight_delta>0 and representation_delta>0 and np.isfinite(grad)
    c.put(c.OUT/'engineering_preflight.json',dict(synthetic_only=True,discarded_training=True,split_max_abs_difference=delta,encoder_weight_L2_delta=weight_delta,representation_L2_delta=representation_delta,gradient_norm=grad,seconds=time.time()-start,cache_batch=cache_batch,inference_benchmark=benchmark,PASS=True))
    print('preflight PASS',delta,weight_delta,representation_delta,flush=True)
if __name__=='__main__':main()
