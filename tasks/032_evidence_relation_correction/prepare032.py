"""Align only audited development materials; keep confirmation GT separate."""
import json,math,subprocess,importlib.metadata as md
from collections import Counter
import common032 as c
P=c.ROOT/'outputs';O=c.OUT/'preparation_001'
SOURCES=['029_semantic_information_gate/preparation_001/full_rows.jsonl','031_training_expansion_confirmation/features_001/rows.jsonl','031_training_expansion_confirmation/judge_inputs_001/materials.jsonl','024_lambda2_transfer_validation/preparation_001/jobs.jsonl','026_frozen_sd_patient_transfer/preparation_001/inputs.jsonl','031_training_expansion_confirmation/planning_001/split.json']
def main():
    c.require(not O.exists(),'Preparation already exists; do not overwrite')
    split=c.read(P/SOURCES[-1]);train=set(split['original16']+split['expansion12']);test=set(split['confirmation12'])
    c.require(not train&test and len(train)==28 and len(test)==12,'031 patient boundary')
    rows=c.lines(P/SOURCES[0])+c.lines(P/SOURCES[1]);c.require(len(rows)==3675,'Expected all 3675 claims')
    mats={r['proposition_id']:r for r in c.lines(P/SOURCES[2])+c.lines(P/SOURCES[4])}
    for j in c.lines(P/SOURCES[3]):
        v=json.loads(j['body']['messages'][-1]['content']);pid=j['proposition_id']
        if pid in mats:c.require(mats[pid]['text']==v['proposition'] and mats[pid]['reference']==v['reference'],'Repeated material mismatch')
        else:mats[pid]=dict(text=v['proposition'],reference=v['reference'])
    ids={r['proposition_id'] for r in rows};c.require(len(ids)==3675 and ids<=set(mats),'Unique material coverage')
    allowed={r['proposition_id'] for r in rows if r['subject_id'] in train};gt=c.scoped_gt(allowed)
    clean=[];labels=[]
    for r in rows:
        pid=r['proposition_id'];sid=r['subject_id'];c.require(sid in train|test,'Unexpected patient')
        sc=[float(r['scores'][k]) for k in c.LABELS];c.require(all(0<=x<=100 for x in sc) and abs(sum(sc)-100)<1e-6,'Invalid score')
        z=[math.log(max(x/100,1e-6)) for x in sc]
        decode=lambda b:0 if z[0]+b>max(z[1:]) else (1 if z[1]>=z[2] else 2)
        c.require(decode(0)==r['u0'] and decode(2)==r['u2'],'Frozen lambda labels differ')
        clean.append(dict(proposition_id=pid,subject_id=sid,author_type=r['author_type'],split='train' if sid in train else 'confirmation',scores=sc,u0=r['u0'],u2=r['u2'],candidate=bool(r['candidate']),text=mats[pid]['text'],reference=mats[pid]['reference']))
        if sid in train:labels.append(dict(proposition_id=pid,human_gt=gt[pid]))
    clean.sort(key=lambda r:r['proposition_id']);O.mkdir(parents=True)
    c.jsonl(O/'inputs_blind.jsonl',clean);c.jsonl(O/'training_labels.jsonl',labels);c.put(O/'split.json',split)
    order=sorted(train,key=lambda s:c.digest(['032-train-fold-v1',s]));folds=[]
    for k in range(4):
        valid=order[k::4];fit=[s for s in order if s not in valid]
        c.require(set(fit).isdisjoint(valid) and set(fit+valid)==train,'Inner patient overlap')
        folds.append(dict(fold=k,training_patients=fit,validation_patients=valid))
    c.put(O/'folds.json',folds)
    for name in ['config.json','protocol.md']:(O/name).write_bytes((c.TASK/name).read_bytes())
    versions={}
    for p in ['torch','transformers','numpy','scipy','pandas','scikit-learn','huggingface-hub','safetensors']:
        try:versions[p]=md.version(p)
        except md.PackageNotFoundError:versions[p]=None
    c.put(O/'environment.json',dict(python=__import__('sys').version,executable=__import__('sys').executable,versions=versions))
    c.put(O/'scope.json',dict(n=len(clean),patients=40,train_claims=len(labels),confirmation_claims=sum(r['split']=='confirmation' for r in clean),candidates=sum(r['candidate'] for r in clean),train_GT_counts=dict(Counter(gt.values())),API_calls=0))
    c.put(O/'manifest.json',dict(created_utc=c.now(),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sources={str(Path):c.sha(P/Path) for Path in SOURCES},files={p.name:c.sha(p) for p in O.iterdir() if p.is_file()},code={p.name:c.sha(p) for p in c.TASK.glob('*.py')},confirmation_GT_connected=False))
    c.state('prepared',state='ready',n=len(clean));print('Prepared 3675 inputs; labels available only for 28 training patients',flush=True)
if __name__=='__main__':main()
