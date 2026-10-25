"""030 offline I/O and deterministic GT-blind patient schedules."""
from pathlib import Path
import hashlib,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/030_gate_training_stability';PREP=OUT/'preparation_001'
sys.path.insert(0,str(ROOT/'tasks/029_semantic_information_gate'))
import common029 as v
import learning029 as learning
import evaluate029 as evaluation
old=v.old;frontier=v.frontier;LABELS=v.LABELS
read=v.read;lines=v.lines;put=v.put;jsonl=v.jsonl;csvwrite=v.csvwrite;csvread=v.csvread;write_text=v.write_text;sha=v.sha;now=v.now;require=v.require;offline=v.offline;environment=v.environment
def digest(value):return hashlib.sha256(v.json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def rank(pool,held,rep,seed):return sorted(pool,key=lambda sid:hashlib.sha256(f'{seed}|{rep}|{held}|{sid}'.encode()).hexdigest())
def model_id(method,patients):return method+'_'+digest(sorted(patients))[:20]
def schedule(groups,config):
    patients=sorted(groups);sweeps=[];units=[];seen={}
    bins=[dict(bin=f'size_{k:02}',kind='size',k=k,composition=None) for k in config['training_sizes']]+[dict(bin='source_'+name,kind='source',k=config['source_size'],composition=counts) for name,counts in config['source_compositions'].items()]
    for spec in bins:
        for rep in range(config['repetitions']):
            sid=f"{spec['bin']}_r{rep:02}";members=[]
            for held in patients:
                ordered=rank([p for p in patients if p!=held],held,rep,config['hash_seed'])
                if spec['composition'] is None:train=ordered[:spec['k']]
                else:
                    train=[]
                    for group,count in zip(('025','026'),spec['composition']):
                        available=[p for p in ordered if groups[p]==group];require(len(available)>=count,'Impossible source composition');train+=available[:count]
                require(len(train)==spec['k'] and held not in train,'Invalid plan')
                members.append(dict(unit_id=sid+'_'+held,sweep_id=sid,bin=spec['bin'],kind=spec['kind'],rep=rep,k=spec['k'],held_patient=held,train_patients=sorted(train),train_025=sum(groups[p]=='025' for p in train),train_026=sum(groups[p]=='026' for p in train)))
            key=digest([(u['held_patient'],u['train_patients']) for u in members]);canonical=seen.setdefault((spec['bin'],key),sid)
            sweeps.append(dict(**spec,rep=rep,sweep_id=sid,canonical_sweep=canonical,plan_hash=key,units=[u['unit_id'] for u in members]));units.extend(members)
    return sweeps,units
def model_probability(meta,rows):
    if meta['fallback']:return np.full(len(rows),meta['constant_probability'])
    from scipy.special import expit
    names=meta['features'];x=np.array([[r['features'][n] for n in names] for r in rows],float).reshape(len(rows),len(names))
    return expit(((x-np.array(meta['mean']))/np.array(meta['scale']))@np.array(meta['coef'])+meta['intercept'])
def summary(values):
    x=np.array([v for v in values if v is not None and np.isfinite(v)],float)
    return dict(n=len(x),mean=float(np.mean(x)) if len(x) else None,median=float(np.median(x)) if len(x) else None,p10=float(np.percentile(x,10)) if len(x) else None,p90=float(np.percentile(x,90)) if len(x) else None,min=float(x.min()) if len(x) else None,max=float(x.max()) if len(x) else None)
def point(rows,p):return evaluation.point(rows,p)
def verify():
    m=read(PREP/'manifest.json')
    for section in ('sources','files','code'):
        for p,h in m[section].items():require(sha(ROOT/p)==h,'Frozen content changed '+p)
    require(environment()['versions']==read(PREP/'environment.json')['versions'],'Environment changed')
    return m
