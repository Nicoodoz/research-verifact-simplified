"""108 minimal original-lower23/top-layer GPU path; import/prepare never uses CUDA.

The CPU preparation copies approximately1GB of original weights and complete
token windows, rather than the22.9GB lower23 subset. A separately supplied
decision binds candidate, instance, deadline and budget before any GPU work.
No SSH, installation, paid API or platform operation is performed here.
"""
from pathlib import Path
import argparse
import gc
import json
import math
import os
import platform
import random
import shutil
import sys
import time
import common108 as c

ORIGINAL_WEIGHTS_SHA='c03cd208bf920b4fbbb182a0535859a566e8acc3477d2b536bf87b769978524b'
ORIGINAL_REVISION='b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7'


def resolve(root,value):
    path=Path(value);return path if path.is_absolute() else Path(root)/path


def atomic_torch(path,value,torch):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix(path.suffix+'.tmp')
    torch.save(value,temporary);os.replace(temporary,path)


def prepare(specification,destination):
    """CPU-only compact complete-window package, never an old092 best.pt."""
    import numpy as np
    import torch
    from safetensors import safe_open
    specification=Path(specification);spec=c.read(specification);destination=Path(destination)
    if destination.exists():raise FileExistsError('Use a new frozen108 package directory')
    splits=c.read(spec['split_path']);rows={r['id']:r for r in c.rows(spec['rows_path'])};bags={r['id']:r for r in c.rows(spec['bags_path'])}
    identifiers=[i for key in ('train','validation','selection') for i in splits[key]]
    if len(identifiers)!=len(set(identifiers)) or len(splits['selection'])!=500:raise ValueError('Split overlap or wrong fixed500')
    patients={key:{rows[i]['sid'] for i in splits[key]} for key in splits}
    if patients['train']&patients['validation'] or (patients['train']|patients['validation'])&patients['selection']:raise ValueError('Patient leakage')
    windows=c.rows(c.ROOT/'.local_models/092/windows.jsonl');used=sorted({w for i in identifiers for w in bags[i]['windows']})
    if any(len(windows[w]['input_ids'])!=512 for w in used):raise ValueError('Unexpected original window shape; preserve full windows rather than truncate')
    original=c.ROOT/'.local_models/032/deberta_v3_nli';top_path=c.ROOT/'.local_models/092/pretrained_top.pt'
    if c.sha(original/'model.safetensors')!=ORIGINAL_WEIGHTS_SHA:raise ValueError('Original encoder revision mismatch')
    top=torch.load(top_path,map_location='cpu',weights_only=True)
    with safe_open(original/'model.safetensors',framework='pt',device='cpu') as source:
        names=[name for name in source.keys() if name.startswith('deberta.encoder.layer.23.')]
        if len(names)!=16 or not all(torch.equal(top['layer'][name.removeprefix('deberta.encoder.layer.23.')],source.get_tensor(name).float()) for name in names):raise ValueError('Top block is not original pretrained layer23')
    if torch.cuda.is_initialized():raise RuntimeError('CPU packaging unexpectedly initialized CUDA')
    destination.mkdir(parents=True);(destination/'base').mkdir();lookup={old:new for new,old in enumerate(used)}
    for name in ('config.json','model.safetensors'):shutil.copyfile(original/name,destination/'base'/name)
    shutil.copyfile(top_path,destination/'pretrained_top.pt')
    np.save(destination/'tokens.npy',np.asarray([windows[w]['input_ids'] for w in used],dtype=np.int32))
    c.putl(destination/'rows.jsonl',[rows[i] for i in identifiers])
    c.putl(destination/'bags.jsonl',[dict(id=i,windows=[lookup[w] for w in bags[i]['windows']],source_windows=bags[i]['windows'],
        reference_sha256=bags[i]['reference_sha256'],claim_sha256=bags[i]['claim_sha256']) for i in identifiers])
    c.put(destination/'splits.json',splits)
    flat_source=Path(spec.get('cpu_flat_predictions_path',c.OUT/'cpu/flat_ce_predictions.jsonl'))
    if not flat_source.is_file():raise FileNotFoundError('Completed cheap flat_ce predictions required before GPU package')
    shutil.copyfile(flat_source,destination/'cpu_flat_predictions.jsonl')
    settings=dict(seed=92027,epochs=5,head_lr=.001,encoder_lr=.00002,weight_decay=.01,dropout=.1,batch_size=8,gradient_clip=1.)
    settings.update(spec.get('settings',{}));c.put(destination/'settings.json',settings)
    script_root=destination/'tasks/108_semantic_hierarchy';script_root.mkdir(parents=True)
    for name in ('gpu108.py','common108.py','model108.py','requirements108.txt'):shutil.copyfile(c.TASK/name,script_root/name)
    metrics_root=destination/'tasks/092_task_adapted_verifier';metrics_root.mkdir(parents=True)
    shutil.copyfile(c.ROOT/'tasks/092_task_adapted_verifier/metrics092.py',metrics_root/'metrics092.py')
    files={p.relative_to(destination).as_posix():c.sha(p) for p in destination.rglob('*') if p.is_file()}
    result=dict(task=108,original_revision=ORIGINAL_REVISION,files=files,windows=len(used),tokens=len(used)*512,
        package_bytes=sum((destination/name).stat().st_size for name in files),lower23_subset_bytes=len(used)*512*1024*2,
        splits={key:dict(N=len(ids),patients=len(patients[key]),windows=sum(len(bags[i]['windows']) for i in ids)) for key,ids in splits.items()},
        maximum_windows_per_bag=max(len(bags[i]['windows']) for i in identifiers),original_top_exact_all16=True,
        old_supervised_checkpoint_used=False,CUDA_initialized=False)
    c.put(destination/'manifest.json',result);return result


def verify(bundle):
    bundle=Path(bundle).resolve();manifest=c.read(bundle/'manifest.json')
    if manifest['task']!=108 or manifest['original_revision']!=ORIGINAL_REVISION:raise ValueError('Wrong108 package')
    for name,wanted in manifest['files'].items():
        path=(bundle/name).resolve()
        if not path.is_relative_to(bundle) or not path.is_file() or c.sha(path)!=wanted:raise ValueError('Bundle mismatch: '+name)
    # The loop already hashed this870MB file; compare its frozen expected hash
    # instead of reading the full encoder a second time.
    if manifest['files'].get('base/model.safetensors')!=ORIGINAL_WEIGHTS_SHA:raise ValueError('Task-adapted encoder forbidden')
    return manifest


def check_deadline(decision,remaining=0.):
    now=time.time();used=decision.get('prior_gpu_cny',0.)+(now-decision['billing_start_epoch'])*decision['hourly_cny']/3600
    if now+remaining>=decision['deadline_epoch'] or used+remaining*decision['hourly_cny']/3600>decision['cap_cny']-.10:raise TimeoutError('108 complete remaining work does not fit fixed time/fee limit')
    return used


def load_decision(path,bundle):
    decision=c.read(path)
    if platform.system()!='Linux' or decision.get('task')!=108 or decision.get('bound_instance')!=platform.node():raise PermissionError('Bound108 Linux instance required')
    if decision.get('gpu_go') is not True or decision.get('candidate') not in ('hier_shared','hier_pool'):raise PermissionError('CPU screen has not selected one allowed GPU candidate')
    if decision['bundle_sha256']!=c.sha(Path(bundle)/'manifest.json'):raise ValueError('CPU decision binds a different package')
    if decision.get('cpu_collapse') is not False:raise PermissionError('Collapsed/undecided CPU screen cannot launch GPU')
    if decision.get('probe_only') and (decision['candidate']!='hier_pool' or decision['deadline_epoch']-decision['preparation_start_epoch']>45*60 or decision['cap_cny']>2):raise PermissionError('No-signal probe is fixed hier_pool within45min/2yuan')
    if decision['hourly_cny']<=0 or decision['deadline_epoch']<=time.time() or decision['cap_cny']<=0:raise ValueError('Actual current price/time limits required')
    check_deadline(decision);return decision


def seed_all(seed,torch,np):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)


def make_adapter(bundle,mode,settings,torch):
    from torch import nn
    from transformers import AutoConfig
    from transformers.models.deberta_v2.modeling_deberta_v2 import DebertaV2Layer,build_relative_position
    from model108 import Head
    class Adapter(nn.Module):
        def __init__(self):
            super().__init__();cfg=AutoConfig.from_pretrained(bundle/'base',local_files_only=True)
            cfg.hidden_dropout_prob=0.;cfg.attention_probs_dropout_prob=0.;self.cfg=cfg
            self.layer=DebertaV2Layer(cfg);self.head=Head(mode,dropout=settings['dropout'])
            original=torch.load(bundle/'pretrained_top.pt',map_location='cpu',weights_only=True)
            self.layer.load_state_dict(original['layer'],strict=True);self.register_buffer('relative',original['relative'])
        def encode(self,h,mask):
            attention=mask[:,None,None,:]*mask[:,None,:,None]
            relative=build_relative_position(h,h,bucket_size=self.cfg.position_buckets,max_position=self.cfg.max_position_embeddings)
            result,_=self.layer(h,attention,relative_pos=relative,rel_embeddings=self.relative)
            return result[:,0]
    return Adapter().cuda()


class Data:
    def __init__(self,bundle,lower,torch,np,window_microbatch=8):
        self.rows={r['id']:r for r in c.rows(bundle/'rows.jsonl')};self.bags={r['id']:r['windows'] for r in c.rows(bundle/'bags.jsonl')}
        self.splits=c.read(bundle/'splits.json');self.lower=lower;self.torch=torch;self.np=np;self.window_microbatch=window_microbatch
    def features(self,net,identifier):
        parts=[]
        windows=self.bags[identifier]
        for start in range(0,len(windows),self.window_microbatch):
            which=windows[start:start+self.window_microbatch]
            h=self.torch.from_numpy(self.np.array(self.lower[which],dtype=self.np.float32)).cuda()
            mask=self.torch.ones((len(which),h.shape[1]),device='cuda',dtype=self.torch.long)
            parts.append(net.encode(h,mask))
        # Every original window is retained, including a short compute tail.
        return self.torch.cat(parts).float()
    def forward(self,net,identifier):return net.head(self.features(net,identifier))
    def predict(self,net,ids,decision,branches=False):
        net.eval();probabilities=[];details=[]
        with self.torch.inference_mode(),self.torch.autocast('cuda',dtype=self.torch.float16):
            for identifier in ids:
                check_deadline(decision);z=self.features(net,identifier);probabilities.append(net.head(z).exp().float().cpu().numpy())
                if branches:
                    group=self.torch.zeros(len(z),device='cuda',dtype=self.torch.long);raw=net.head.branch_logits(z,group)
                    if net.head.mode=='flat_ce':details.append(dict(flat_logits=raw.float().cpu()[0].tolist()))
                    else:
                        a,conditional=raw;details.append(dict(addressed_logit=float(a[0]),conditional_logit=float(conditional[0]),
                            addressed_probability=float(a.float().sigmoid()[0]),conditional_supported_probability=float(conditional.float().sigmoid()[0])))
        probability=self.np.asarray(probabilities)
        return (probability,details) if branches else probability


def train(data,bundle,work,mode,settings,decision,torch,np):
    from torch.nn import functional as F
    sys.path.insert(0,str(bundle/'tasks/092_task_adapted_verifier'))
    from metrics092 import metrics
    seed_all(settings['seed'],torch,np);net=make_adapter(bundle,mode,settings,torch)
    optimizer=torch.optim.AdamW([dict(params=net.layer.parameters(),lr=settings['encoder_lr']),dict(params=net.head.parameters(),lr=settings['head_lr'])],weight_decay=settings['weight_decay'])
    scaler=torch.amp.GradScaler('cuda');order_rng=np.random.default_rng(settings['seed']);history=[];best=None;updates=skipped=0;begin=time.time()
    train_ids=data.splits['train'];valid_ids=data.splits['validation'];folder=work/mode;folder.mkdir(parents=True,exist_ok=True)
    for epoch in range(1,settings['epochs']+1):
        order=order_rng.permutation(len(train_ids));net.train()
        for start in range(0,len(order),settings['batch_size']):
            check_deadline(decision);which=[train_ids[int(i)] for i in order[start:start+settings['batch_size']]];optimizer.zero_grad(set_to_none=True)
            for identifier in which:
                with torch.autocast('cuda',dtype=torch.float16):
                    logp=data.forward(net,identifier);target=torch.tensor([c.LABELS.index(data.rows[identifier]['GT'])],device='cuda')
                    loss=F.nll_loss(logp[None],target)/len(which)
                if not torch.isfinite(loss):raise FloatingPointError('Nonfinite complete-bag NLL')
                scaler.scale(loss).backward()
            scaler.unscale_(optimizer);norm=torch.nn.utils.clip_grad_norm_(net.parameters(),settings['gradient_clip'])
            # Original092 FP16 GradScaler handles transient overflow by skipping
            # an update and reducing scale. Preserve that behavior and report it.
            old=scaler.get_scale();scaler.step(optimizer);scaler.update();successful=int(scaler.get_scale()>=old)
            updates+=successful;skipped+=1-successful
        probability=data.predict(net,valid_ids,decision);target=np.asarray([c.LABELS.index(data.rows[i]['GT']) for i in valid_ids]);values=metrics(target,probability.argmax(1),probability)
        key=(values['MCC'],values['PA'],values['Macro_F1'],-values['false_S']);history.append(dict(epoch=epoch,validation=values))
        if best is None or key>tuple(best['key']):best=dict(epoch=epoch,key=key);atomic_torch(folder/'best.pt',net.state_dict(),torch)
        atomic_torch(folder/'last.pt',dict(net=net.state_dict(),optimizer=optimizer.state_dict(),scaler=scaler.state_dict(),epoch=epoch,
            seed=settings['seed'],settings=settings,best=best,python_rng=random.getstate(),numpy_rng=np.random.get_state(),
            torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),order_rng=order_rng.bit_generator.state,
            bundle_sha256=c.sha(bundle/'manifest.json')),torch)
        c.put(folder/'history.json',history);print(c.canonical(dict(arm=mode,epoch=epoch,best=best)),flush=True)
    if updates==0:raise FloatingPointError('No successful top-layer optimizer update')
    net.load_state_dict(torch.load(folder/'best.pt',map_location='cpu',weights_only=True),strict=True)
    selected=data.splits['selection'];probability,branches=data.predict(net,selected,decision,branches=True)
    c.putl(folder/'predictions.jsonl',[dict(id=i,arm=mode,sid=data.rows[i]['sid'],prediction=c.LABELS[int(p.argmax())],probabilities=p.tolist(),branches=branch) for i,p,branch in zip(selected,probability,branches)])
    c.put(folder/'complete.json',dict(arm=mode,best=best,updates=updates,skipped_FP16_updates=skipped,seconds=time.time()-begin,selection_N=len(selected),
        encoder_trainable_parameters=sum(p.numel() for p in net.layer.parameters()),complete_original_windows=True,
        original_pretrained_initialization=True,old092_supervised_checkpoint_used=False,bundle_sha256=c.sha(bundle/'manifest.json')))
    del net,optimizer,scaler;gc.collect();torch.cuda.empty_cache()


def candidate_screen(bundle,work,candidate):
    """Frozen point screen against the cheap flat head; not a fair GPU contrast."""
    import numpy as np
    sys.path.insert(0,str(bundle/'tasks/092_task_adapted_verifier'))
    from metrics092 import metrics
    rows={r['id']:r for r in c.rows(bundle/'rows.jsonl')};selection=c.read(bundle/'splits.json')['selection']
    baseline={r['id']:r for r in c.rows(bundle/'cpu_flat_predictions.jsonl')}
    newer={r['id']:r for r in c.rows(work/candidate/'predictions.jsonl')}
    if set(baseline)!=set(selection) or set(newer)!=set(selection):raise ValueError('Incomplete500 in candidate continuation screen')
    panels={};guards=[];signals=[]
    for panel in ('natural','pressure'):
        ids=[i for i in selection if rows[i]['panel']==panel];truth=[c.LABELS.index(rows[i]['GT']) for i in ids]
        old=metrics(truth,[c.LABELS.index(baseline[i]['prediction']) for i in ids]);new=metrics(truth,[c.LABELS.index(newer[i]['prediction']) for i in ids])
        dm=new['MCC']-old['MCC'];dp=new['PA']-old['PA'];df=new['false_S']-old['false_S']
        dr=[a-b for a,b in zip(new['recall'],old['recall'])]
        guard=dm>=-.03-1e-12 and dp>=-.03-1e-12 and df<=2 and min(dr[1:])>=-.10-1e-12
        if panel=='natural':guard=guard and dr[0]>=-.03-1e-12
        signal=dm>=.015-1e-12 or (df<=-2 and dp>=-.02-1e-12)
        panels[panel]=dict(cheap_fixed_feature=old,GPU_candidate=new,delta_MCC=dm,delta_PA=dp,delta_false_S=df,delta_recall=dr,guard=guard,signal=signal)
        guards.append(guard);signals.append(signal)
    result=dict(panels=panels,continue_to_fair_flat_top_control=all(guards) and any(signals),
        cheap_fixed_feature_is_not_fair_GPU_control=True,selection_not_used_to_select_epoch_or_tune_hyperparameters=True)
    c.put(work/'candidate_screen.json',result);return result


def run(bundle,work,decision_path,window_microbatch=8,cache_batch=8):
    bundle=Path(bundle);work=Path(work);manifest=verify(bundle);decision=load_decision(decision_path,bundle);work.mkdir(parents=True,exist_ok=True)
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
    import numpy as np
    import torch
    import importlib.metadata as metadata
    from transformers import AutoModel
    versions={name:metadata.version(name) for name in ('torch','transformers','tokenizers','numpy','safetensors')}
    if versions['transformers']!='4.56.1':raise RuntimeError('Use isolated108 transformers4.56.1; do not overwrite107 environment')
    c.put(work/'environment.json',dict(versions=versions,Python=sys.version,instance=platform.node(),window_microbatch=window_microbatch,cache_batch=cache_batch))
    if not torch.cuda.is_available():raise RuntimeError('This entry requires the bound108 GPU')
    if shutil.disk_usage(work).free<manifest['lower23_subset_bytes']+2*1024**3:raise RuntimeError('Insufficient existing disk for complete lower23 subset; no automatic expansion')
    settings=c.read(bundle/'settings.json');seed_all(settings['seed'],torch,np);tokens=np.load(bundle/'tokens.npy',mmap_mode='r')
    encoder=AutoModel.from_pretrained(bundle/'base',local_files_only=True,torch_dtype=torch.float16).cuda().eval()
    for p in encoder.parameters():p.requires_grad_(False)
    # Original first23 layers only. The untouched24th layer is trained separately.
    encoder.encoder.layer=torch.nn.ModuleList(list(encoder.encoder.layer)[:23])
    warm=min(cache_batch,len(tokens));batch=torch.from_numpy(np.array(tokens[:warm],dtype=np.int64)).cuda();mask=torch.ones_like(batch)
    with torch.inference_mode():encoder(input_ids=batch,attention_mask=mask)
    torch.cuda.synchronize();begin=time.perf_counter()
    measured_windows=0
    with torch.inference_mode():
        for start in range(0,min(len(tokens),cache_batch*4),cache_batch):
            ids=torch.from_numpy(np.array(tokens[start:start+cache_batch],dtype=np.int64)).cuda()
            encoder(input_ids=ids,attention_mask=torch.ones_like(ids));measured_windows+=len(ids)
    torch.cuda.synchronize();cache_speed=measured_windows/(time.perf_counter()-begin)
    # Before full encoding, benchmark one complete largest training bag using
    # original lower states. These disposable models never seed formal training.
    bags={r['id']:r['windows'] for r in c.rows(bundle/'bags.jsonl')};splits=c.read(bundle/'splits.json')
    longest=max(splits['train'],key=lambda i:len(bags[i]));indices=bags[longest]
    with torch.inference_mode():
        probe=[]
        for index in indices:
            inp=torch.from_numpy(np.array(tokens[index:index+1],dtype=np.int64)).cuda();probe.append(encoder(input_ids=inp,attention_mask=torch.ones_like(inp)).last_hidden_state.detach())
    del encoder,batch,mask,inp;gc.collect();torch.cuda.empty_cache();timings={}
    rows={r['id']:r for r in c.rows(bundle/'rows.jsonl')}
    for mode in ('flat_ce',decision['candidate']):
        seed_all(settings['seed'],torch,np);net=make_adapter(bundle,mode,settings,torch);net.train();begin=time.perf_counter();torch.cuda.reset_peak_memory_stats()
        with torch.autocast('cuda',dtype=torch.float16):
            z=torch.cat([net.encode(torch.cat(probe[start:start+window_microbatch]).float(),
                torch.ones((len(probe[start:start+window_microbatch]),512),device='cuda',dtype=torch.long)) for start in range(0,len(probe),window_microbatch)])
            logp=net.head(z.float())
            loss=torch.nn.functional.nll_loss(logp[None],torch.tensor([c.LABELS.index(rows[longest]['GT'])],device='cuda'))
        loss.backward();torch.cuda.synchronize()
        if not torch.isfinite(loss) or not any(p.grad is not None and p.grad.abs().sum()>0 for p in net.layer.parameters()):raise RuntimeError('Top layer failed real gradient check')
        timings[mode]=dict(seconds_per_window=(time.perf_counter()-begin)/len(probe),peak_allocated_bytes=torch.cuda.max_memory_allocated())
        del net,loss,z,logp;gc.collect();torch.cuda.empty_cache()
    del probe
    counts={key:sum(len(bags[i]) for i in ids) for key,ids in splits.items()}
    # Backward time bounds validation/prediction too;1.5 margin includes Python,
    # optimizer and100MB checkpoints. Measured upload/setup already consumed time.
    cache_seconds=len(tokens)/cache_speed
    train_seconds=sum(t['seconds_per_window']*(settings['epochs']*(counts['train']+counts['validation'])+counts['selection'])*1.5 for t in timings.values())
    projected=cache_seconds+train_seconds+120
    receipt=dict(cache_windows_per_second=cache_speed,cache_measured_windows=measured_windows,cache_batch=cache_batch,window_microbatch=window_microbatch,
        training_probes=timings,remaining_cache_seconds=cache_seconds,
        remaining_two_arm_seconds=train_seconds,remaining_total_seconds=projected,all_original_windows=len(tokens),counts=counts,
        current_estimated_gpu_cny=check_deadline(decision),deadline_epoch=decision['deadline_epoch'],whole_run_fits=False)
    try:check_deadline(decision,projected)
    except TimeoutError:c.put(work/'gpu_gate.json',receipt);raise
    receipt['whole_run_fits']=True;c.put(work/'gpu_gate.json',receipt)
    # Reload original frozen encoder after discarding every disposable top probe.
    encoder=AutoModel.from_pretrained(bundle/'base',local_files_only=True,torch_dtype=torch.float16).cuda().eval()
    for p in encoder.parameters():p.requires_grad_(False)
    encoder.encoder.layer=torch.nn.ModuleList(list(encoder.encoder.layer)[:23])
    lower=np.lib.format.open_memmap(work/'lower23.npy',mode='w+',dtype='float16',shape=(len(tokens),512,1024))
    with torch.inference_mode():
        for start in range(0,len(tokens),cache_batch):
            check_deadline(decision);ids=torch.from_numpy(np.array(tokens[start:start+cache_batch],dtype=np.int64)).cuda()
            output=encoder(input_ids=ids,attention_mask=torch.ones_like(ids)).last_hidden_state
            lower[start:start+len(ids)]=output.cpu().numpy()
    lower.flush();del encoder,ids,output;gc.collect();torch.cuda.empty_cache();data=Data(bundle,lower,torch,np,window_microbatch=window_microbatch)
    candidate=decision['candidate'];train(data,bundle,work,candidate,settings,decision,torch,np)
    screen=candidate_screen(bundle,work,candidate);actual_arms=[candidate]
    if screen['continue_to_fair_flat_top_control']:
        check_deadline(decision);train(data,bundle,work,'flat_ce',settings,decision,torch,np);actual_arms.append('flat_ce')
    c.put(work/'complete.json',dict(task=108,arms=actual_arms,fair_control_run='flat_ce' in actual_arms,GPU_model=torch.cuda.get_device_name(),
        paid_API_calls=0,full_input_and_all_windows=True,bundle_sha256=c.sha(bundle/'manifest.json'),time=time.time()))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','verify','run'])
    parser.add_argument('--data',type=Path);parser.add_argument('--bundle',type=Path,required=True)
    parser.add_argument('--work',type=Path);parser.add_argument('--decision',type=Path)
    parser.add_argument('--window-microbatch',type=int,choices=[1,2,4,8],default=8)
    parser.add_argument('--cache-batch',type=int,choices=[1,2,4,8],default=8);args=parser.parse_args()
    if args.action=='prepare':print(c.canonical(prepare(args.data,args.bundle)))
    elif args.action=='verify':print(c.canonical(verify(args.bundle)))
    else:
        if args.work is None or args.decision is None:parser.error('Bound CPU decision and work path required')
        try:run(args.bundle,args.work,args.decision,window_microbatch=args.window_microbatch,cache_batch=args.cache_batch)
        finally:
            # The separately bound lifecycle108 watcher owns platform shutdown.
            c.put(args.work/'finish_requested.json',dict(reason='gpu108_entry_finished_or_failed',epoch=time.time()))


if __name__=='__main__':main()
