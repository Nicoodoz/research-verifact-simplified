"""One fixed effective-update midpoint of107 and120; CPU only."""
from pathlib import Path
import argparse,hashlib,json


def combine(a0,b0,s0,a1,b1,s1,alpha):
    import torch
    a=torch.cat(((1-alpha)*s0*a0,alpha*s1*a1),dim=0)
    b=torch.cat((b0,b1),dim=1)
    return a.contiguous(),b.contiguous()


def compose(anchor,candidate,out):
    import torch
    from safetensors.torch import load_file,save_file
    torch.set_num_threads(4)
    cfg0=json.loads((anchor/'adapter_config.json').read_text())
    cfg1=json.loads((candidate/'adapter_config.json').read_text())
    for cfg in (cfg0,cfg1):
        if cfg['r']!=16 or cfg['lora_alpha']!=32 or any(cfg.get(k) for k in
             ('use_rslora','use_dora','modules_to_save','rank_pattern','alpha_pattern')) or cfg['bias']!='none':
            raise ValueError('Expected the retained plain rank16/alpha32 LoRA sources')
    if cfg0['target_modules']!=cfg1['target_modules']:raise ValueError('Different target modules')
    w0=load_file(str(anchor/'adapter_model.safetensors'));w1=load_file(str(candidate/'adapter_model.safetensors'))
    if set(w0)!=set(w1):raise ValueError('Different adapter tensor keys')
    weights={};errors=[]
    for key in sorted(w0):
        if not key.endswith('.lora_A.weight'):continue
        kb=key.replace('.lora_A.weight','.lora_B.weight')
        a0,b0,a1,b1=w0[key],w0[kb],w1[key],w1[kb]
        if any(t.dtype!=torch.float32 for t in (a0,b0,a1,b1)):raise ValueError('Preserve original FP32 factors')
        a,b=combine(a0,b0,2.,a1,b1,2.,.5)
        # Check every module on three output coordinates without full dense BA.
        x=torch.linspace(-.5,.5,a.shape[1]);idx=[0,b.shape[0]//2,b.shape[0]-1]
        expected=b0[idx]@(a0@x)+b1[idx]@(a1@x)
        actual=b[idx]@(a@x);error=float((actual-expected).abs().max())
        if error>1e-4*max(1.,float(expected.abs().max())):raise ValueError('Effective update mismatch')
        errors.append(error);weights[key]=a;weights[kb]=b
    if set(weights)!=set(w0):raise ValueError('Unexpected non-LoRA tensor')
    out.mkdir(parents=True,exist_ok=True)
    dest=out/'adapter_model.safetensors'
    if dest.exists():raise FileExistsError('Do not overwrite a composed adapter')
    save_file(weights,str(dest),metadata={'format':'pt'})
    cfg=dict(cfg1,r=32,lora_alpha=32,inference_mode=True)
    (out/'adapter_config.json').write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
    def sha(path):
        value=hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
        return value.hexdigest()
    info=dict(alpha=.5,source107_sha256=sha(anchor/'adapter_model.safetensors'),
        source120_sha256=sha(candidate/'adapter_model.safetensors'),adapter_sha256=sha(dest),
        formula='W0 + 0.5*DeltaW107 + 0.5*DeltaW120',rank=32,scaling=1,
        module_count=len(errors),max_effective_probe_error=max(errors),source_factors_unchanged=True,
        factor_average=False,SVD=False,new_training=False)
    (out/'composition.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(info))
    return info


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for field in ('anchor','candidate','out'):p.add_argument('--'+field,type=Path,required=True)
    a=p.parse_args();compose(a.anchor,a.candidate,a.out)
