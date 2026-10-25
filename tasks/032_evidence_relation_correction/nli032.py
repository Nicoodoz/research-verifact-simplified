"""Frozen local NLI on original C48 passages and within-note selected context."""
import os,re,json,time,collections
os.environ['TOKENIZERS_PARALLELISM']='false'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
import numpy as np
import torch
from transformers import AutoTokenizer,AutoModelForSequenceClassification
import common032 as c
HEADER=re.compile(r'(?m)^(\d+)\. Date: ([^\n]+?) \| Text:\s*')
def pieces(reference):
    matches=list(HEADER.finditer(reference));out=[]
    c.require(bool(matches),'C48 record boundaries not found')
    adm='\n'.join(reference.splitlines()[:2])
    for i,m in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(reference)
        meta=m.group(2);body=reference[m.end():end].strip();note=re.search(r'Note ID: ([^,]+)',meta)
        hdr=meta.split(', Note ID:')[0]
        out.append(dict(number=int(m.group(1)),note=note.group(1) if note else str(i),header='Date: '+hdr,body=body,start=m.end(),end=end))
    return adm,out

def build_pairs(rows,tok,cfg):
    pairs=[];lookup={};bags=[];stats=collections.Counter()
    for r in rows:
        hypothesis=tok.encode(r['text'],add_special_tokens=False);capacity=cfg['max_length']-len(hypothesis)-tok.num_special_tokens_to_add(pair=True)
        c.require(capacity>=64,'Claim too long; do not truncate it: '+r['proposition_id'])
        adm,parts=pieces(r['reference']);groups=collections.defaultdict(list)
        for p in parts:groups[p['note']].append(p)
        views=[(0,[p]) for p in parts]+[(1,v) for v in groups.values() if len(v)>1]
        members=[];ct=set(re.findall(r'\b[a-z]{3,}\b',r['text'].lower()))
        for kind,pp in views:
            evidence=adm+'\n'+pp[0]['header']+'\n'+'\n[Other text omitted]\n'.join(p['body'] for p in pp)
            tokens=tok.encode(evidence,add_special_tokens=False)
            starts=list(range(0,max(1,len(tokens)-capacity+1),max(1,capacity-cfg['overlap_tokens'])))
            if starts[-1]+capacity<len(tokens):starts.append(max(0,len(tokens)-capacity))
            for begin in sorted(set(starts)):
                segment=tokens[begin:begin+capacity];key=c.digest([hypothesis,segment])
                if key not in lookup:
                    item=tok.prepare_for_model(segment,pair_ids=hypothesis,add_special_tokens=True,return_token_type_ids=False,truncation=False,return_attention_mask=True)
                    c.require(len(item['input_ids'])<=cfg['max_length'],'NLI context overflow')
                    lookup[key]=len(pairs);pairs.append(dict(key=key,**item))
                st=set(re.findall(r'\b[a-z]{3,}\b',tok.decode(segment).lower()))
                members.append(dict(pair=lookup[key],kind=kind,coverage=len(ct&st)/max(1,len(ct)),records=[p['number'] for p in pp],token_start=begin,token_end=begin+len(segment)))
                stats['passage_windows' if kind==0 else 'note_windows']+=1
        bags.append(dict(proposition_id=r['proposition_id'],members=members))
    stats.update(unique_pairs=len(pairs),claims=len(rows))
    return pairs,bags,dict(stats)

def run():
    c.block_network();cfg=c.read(c.OUT/'preparation_001/config.json');rows=c.lines(c.OUT/'preparation_001/inputs_blind.jsonl')
    asset=c.read(c.OUT/'model_manifest.json');path=c.CACHE/'deberta_v3_nli'
    c.require(asset['revision']==cfg['nli_revision'],'Unexpected NLI revision')
    for name,h in asset['files'].items():c.require(c.sha(path/name)==h['sha256'],'Model asset hash changed '+name)
    tok=AutoTokenizer.from_pretrained(str(path),local_files_only=True,trust_remote_code=False)
    pairs,bags,stats=build_pairs(rows,tok,cfg);out=c.OUT/'nli_001';out.mkdir(exist_ok=True)
    c.jsonl(out/'bags.jsonl',bags);c.put(out/'scope.json',stats)
    fingerprint=c.digest([asset['files'],[p['key'] for p in pairs],cfg['projection_seed'],cfg['projection_dimensions']])
    cache=c.CACHE/'pair_cache';cache.mkdir(parents=True,exist_ok=True);manifest=cache/'manifest.json'
    if manifest.exists():c.require(c.read(manifest)['fingerprint']==fingerprint,'Different input/model cache; do not reuse')
    else:c.put(manifest,dict(fingerprint=fingerprint,n=len(pairs),dimensions=38))
    feature_path=cache/'features.npy';done_path=cache/'done.npy';n=len(pairs)
    x=np.lib.format.open_memmap(feature_path,mode='r+' if feature_path.exists() else 'w+',dtype='float32',shape=(n,38))
    done=np.lib.format.open_memmap(done_path,mode='r+' if done_path.exists() else 'w+',dtype='uint8',shape=(n,))
    todo=sorted(np.flatnonzero(done==0).tolist(),key=lambda i:len(pairs[i]['input_ids']))
    c.state('nli',state='running',completed=int(done.sum()),total=n,scope=stats)
    print('NLI pairs',n,'remaining',len(todo),'device',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU',flush=True)
    device='cuda' if torch.cuda.is_available() else 'cpu';torch.set_num_threads(4)
    if todo:
        dtype=torch.float16 if device=='cuda' else torch.float32
        model=AutoModelForSequenceClassification.from_pretrained(str(path),local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=dtype).to(device).eval()
        labelmap={int(k):str(v).lower() for k,v in model.config.id2label.items()}
        c.require(labelmap=={0:'entailment',1:'neutral',2:'contradiction'},'Unexpected NLI label order')
        rng=np.random.RandomState(cfg['projection_seed']);project=torch.tensor(rng.normal(size=(model.config.hidden_size,32))/np.sqrt(32),dtype=torch.float32,device=device)
        runtime=c.read(c.OUT/'compute_override.json') if (c.OUT/'compute_override.json').exists() else {};batch_size=int(runtime.get('batch_size',cfg['batch_size']));cursor=0;started=time.monotonic()
        while cursor<len(todo):
            ids=todo[cursor:cursor+batch_size]
            batch=tok.pad([{k:pairs[i][k] for k in ['input_ids','attention_mask']} for i in ids],padding=True,return_tensors='pt').to(device)
            try:
                with torch.inference_mode():
                    result=model(**batch,output_hidden_states=True,return_dict=True)
                    prob=result.logits.float().softmax(-1)
                    h=result.hidden_states[-1][:,0].float();h=torch.nn.functional.normalize(h,dim=-1)
                    embedded=torch.nn.functional.normalize(h@project,dim=-1)
                    values=torch.cat([prob,prob.clamp_min(1e-7).log(),embedded],dim=1).cpu().numpy()
                c.require(np.isfinite(values).all(),'Nonfinite NLI output')
            except torch.cuda.OutOfMemoryError:
                if batch_size==1:raise
                batch_size=max(1,batch_size//2);del batch;torch.cuda.empty_cache();print('OOM: smaller computational batch',batch_size,flush=True);continue
            x[ids]=values;x.flush();done[ids]=1;done.flush();cursor+=len(ids)
            del result,batch,h,embedded,values
            if cursor%256<batch_size or cursor==len(todo):
                c.state('nli',state='running',completed=int(done.sum()),total=n,batch_size=batch_size,elapsed_seconds=round(time.monotonic()-started,2))
                print('NLI',int(done.sum()),'/',n,flush=True)
        del model,project
        if device=='cuda':torch.cuda.empty_cache()
    c.require(bool(np.all(done==1)) and np.isfinite(x).all(),'Incomplete NLI cache')
    max_bag=max(len(b['members']) for b in bags);padded=np.zeros((len(rows),max_bag,40),dtype='float32');mask=np.zeros((len(rows),max_bag),dtype=bool)
    for i,b in enumerate(bags):
        for j,m in enumerate(b['members']):
            padded[i,j,:38]=x[m['pair']];padded[i,j,38]=m['kind'];padded[i,j,39]=m['coverage'];mask[i,j]=True
    destination=c.CACHE/'bags.npz';np.savez_compressed(destination,x=padded,mask=mask,ids=np.array([r['proposition_id'] for r in rows]))
    c.put(out/'manifest.json',dict(created_utc=c.now(),model_revision=cfg['nli_revision'],label_order=['entailment','neutral','contradiction'],pair_cache_fingerprint=fingerprint,bags_sha256=c.sha(destination),bag_mapping_sha256=c.sha(out/'bags.jsonl'),max_bag=max_bag,stats=stats,API_calls=0,final_batch_size=locals().get('batch_size',None),dtype='float16' if device=='cuda' else 'float32',device=device))
    c.state('nli_completed',state='ready',completed=n,total=n);print('All NLI features cached',destination,flush=True)
if __name__=='__main__':run()
