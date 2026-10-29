"""Exactly two cat-composed effective LoRA updates on a single shared9B base."""
from pathlib import Path
import argparse,json,sys,time
from runtime110 import c,load,activate,predict,budget,progress
def compose(model,alpha,name,torch):
    model.add_weighted_adapter(['anchor107','update109'],[1-alpha,alpha],name,combination_type='cat')
    checks=[]
    with torch.no_grad():
        for path,m in model.named_modules():
            if not hasattr(m,'lora_A') or name not in m.lora_A:continue
            a0=m.lora_A['anchor107'].weight;b0=m.lora_B['anchor107'].weight;a1=m.lora_A['update109'].weight;b1=m.lora_B['update109'].weight
            # Preserve the source checkpoint FP32 factors even if adapter
            # injection initially created a BF16 destination in this PEFT build.
            if any(t.dtype!=torch.float32 for t in [a0,b0,a1,b1]):raise ValueError('Expected original FP32 LoRA factors')
            m.lora_A[name].weight.data=torch.cat([a0.data*(1-alpha)*m.scaling['anchor107'],a1.data*alpha*m.scaling['update109']],dim=0)
            m.lora_B[name].weight.data=torch.cat([b0.data,b1.data],dim=1)
            a=m.lora_A[name].weight;b=m.lora_B[name].weight;s0=m.scaling['anchor107'];s1=m.scaling['update109'];sm=m.scaling[name]
            if a.shape[0]!=32 or sm!=1 or a0.shape[0]!=16 or a1.shape[0]!=16:raise ValueError('Unexpected cat rank/scaling')
            torch.testing.assert_close(a[:16],a0*(1-alpha)*s0,rtol=0,atol=0);torch.testing.assert_close(a[16:],a1*alpha*s1,rtol=0,atol=0)
            if not torch.equal(b[:,:16],b0) or not torch.equal(b[:,16:],b1):raise ValueError('B concatenation differs')
            # Three sampled output coordinates and one deterministic input vector,
            # across every adapted module, without allocating full dense BA.
            x=torch.linspace(-.5,.5,a.shape[1],device=a.device,dtype=torch.float32);indices=[0,b.shape[0]//2,b.shape[0]-1]
            expected=(1-alpha)*s0*(b0[indices].float()@(a0.float()@x))+alpha*s1*(b1[indices].float()@(a1.float()@x))
            actual=sm*(b[indices].float()@(a.float()@x));error=float((actual-expected).abs().max());scale=max(1.,float(expected.abs().max()))
            if error>1e-4*scale:raise ValueError('Effective BA interpolation check failed')
            checks.append(dict(module=path,rank=32,scaling=sm,max_abs_effective_probe_error=error))
    if not checks:raise ValueError('No LoRA modules composed')
    return dict(alpha=alpha,combination_type='cat',new_rank=32,source_ranks=[16,16],exact_factor_concatenation=True,
        double_activation=False,modules_checked=len(checks),max_effective_probe_error=max(x['max_abs_effective_probe_error'] for x in checks))
def main():
    p=argparse.ArgumentParser()
    for name in ['old','model','work','session','config']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();cfg=c.read(a.config)
    if cfg['candidates']!={'update_quarter':.25,'update_half':.5}:raise ValueError('Only two prespecified candidates')
    if not (a.work/'DIAGNOSTIC_GPU_DONE.json').exists():raise ValueError('Finish192 diagnostic first')
    budget(a.session,3000)
    model,tok,Fast,torch=load(a)
    from peft import PeftModel
    source0=a.old/'bundle/source107/checkpoint_a';source1=a.old/'results/train/checkpoint_a'
    if c.sha(source0/'adapter_model.safetensors')!=cfg['source107_adapter_sha256'] or c.sha(source1/'adapter_model.safetensors')!=cfg['source109_adapter_sha256']:raise ValueError('Wrong original source checkpoints')
    model=PeftModel.from_pretrained(model,source0,adapter_name='anchor107',is_trainable=False)
    model.load_adapter(source1,adapter_name='update109',is_trainable=False);Fast.for_inference(model)
    for name in ['anchor107','update109']:
        conf=model.peft_config[name]
        if conf.r!=16 or conf.lora_alpha!=32 or conf.use_rslora or conf.use_dora or conf.modules_to_save or conf.bias!='none':raise ValueError('Unexpected source LoRA')
    train={r['id']:r for r in c.rows(a.old/'results/train.jsonl')};endpoint=cfg['endpoint_ids'];batches=[dict(batch=n,ids=[i]) for n,i in enumerate(endpoint)]
    endpoint_results={};checks={}
    for source,name,alpha in [('anchor107','endpoint_zero',0.),('update109','endpoint_one',1.)]:
        activate(model,source);predict(a,model,tok,torch,train,batches,'check_'+source,dict(endpoint_source=source))
        checks[name]=compose(model,alpha,name,torch);activate(model,name)
        predict(a,model,tok,torch,train,batches,'check_'+name,dict(endpoint_alpha=alpha))
        original=c.rows(a.work/('check_'+source)/'predictions.jsonl');composed=c.rows(a.work/('check_'+name)/'predictions.jsonl')
        equal=[x['content']==y['content'] and x['finish_reason']==y['finish_reason'] for x,y in zip(original,composed)]
        endpoint_results[name]=dict(N=len(equal),exact_first_output_agreement=sum(equal),verdict_agreement=sum(x['parsed'].get('verdict')==y['parsed'].get('verdict') for x,y in zip(original,composed)))
        if not all(equal):raise RuntimeError('Small real endpoint outputs differ; inspect numerical/activation cause before formal500')
        model.delete_adapter(name)
    c.put(a.work/'endpoint_checks.json',dict(algebra=checks,real=endpoint_results,no_full_old500_replayed=True))
    for name,alpha in cfg['candidates'].items():
        checks[name]=compose(model,alpha,name,torch)
    activate(model,'update_quarter');model.save_pretrained(a.work/'adapters',selected_adapters=list(cfg['candidates']),safe_serialization=True)
    identities={}
    for name,alpha in cfg['candidates'].items():
        folder=a.work/'adapters'/name;identities[name]=dict(candidate=name,alpha=alpha,adapter_sha256=c.sha(folder/'adapter_model.safetensors'))
    c.put(a.work/'composition.json',dict(sources={'107':c.sha(source0/'adapter_model.safetensors'),'109':c.sha(source1/'adapter_model.safetensors')},checks={k:checks[k] for k in cfg['candidates']},identities=identities,
        formula='W0+(1-alpha)*s107*B107*A107+alpha*s109*B109*A109',no_training=True,no_SVD=True,only_one_original9B_backbone=True))
    c.put(a.work/'ADAPTERS_READY.json',identities)
    rows={r['id']:r for r in c.rows(a.old/'bundle/data/eval_inputs.jsonl')};batches=c.read(a.old/'bundle/frozen/eval_batches.json')['batches']
    for name in cfg['candidates']:
        activate(model,name)
        if any(getattr(m,'merged',False) for m in model.modules() if hasattr(m,'lora_A')):raise ValueError('Do not stack a merged source adapter')
        predict(a,model,tok,torch,rows,batches,name,identities[name])
    c.put(a.work/'GPU_TASKS_COMPLETE.json',dict(task=110,candidates=list(cfg['candidates']),new_training=False,new_paid_API_CNY=0,utc=c.utc()))
if __name__=='__main__':main()
