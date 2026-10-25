"""One-time, inspectable task-local derivation of the proven031 executor and C48 path."""
from pathlib import Path
root=Path(__file__).resolve().parents[2];task=Path(__file__).resolve().parent
source=root/'tasks/031_training_expansion_confirmation'
def save(name,text):
    p=task/name
    with p.open('x',encoding='utf-8',newline='\n') as f:f.write(text)
s=(source/'api031.py').read_text(encoding='utf-8')
s=s.replace('common031','common036').replace('80CNY','150CNY').replace("out/'before_models/manifest.json'","out/'final_freeze_001/manifest.json'")
s=s.replace("c.OUT/'before_models/manifest.json'","c.OUT/'final_freeze_001/manifest.json'").replace('>80:', '>c.CAP:').replace("'task_budget80'","'task_budget150'").replace('cap_cny=80','cap_cny=c.CAP')
s=s.replace("api.old.body(text,reference,True)","api.old.body(text,reference,role!='baseline')")
s=s.replace("if a.alias!='account_1'","if a.alias not in ('account_1','account_2')")
save('api036.py',s)
s=(source/'prepare_materials031.py').read_text(encoding='utf-8').replace('common031','common036').replace("'031_embed'","'036_embed'")
s=s.split('    # Price estimation')[0]+'''    out.mkdir(parents=True);c.jsonl(out/'inputs.jsonl',inputs);c.jsonl(out/'corpus.jsonl',corpus);c.jsonl(out/'cached_c48.jsonl',cached);c.jsonl(out/'embedding_jobs.jsonl',embedjobs);c.put(out/'embedding_catalog.json',catalog);keys=sorted(vectors);c.put(out/'embedding_ids.json',keys);np.save(out/'vectors.npy',np.array([vectors[k] for k in keys]),allow_pickle=False);c.put(out/'vector_sources.json',vector_sources)
    c.put(out/'manifest.json',dict(created_utc=c.now(),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sources+[c.OUT/'planning_001/manifest.json']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}))
    print('036 GT-blind materials',len(inputs),'corpus',len(corpus),'cached',len(cached),'embedding jobs',len(embedjobs),flush=True)
if __name__=='__main__':run()
'''
save('materials036.py',s)
s=(source/'pipeline031.py').read_text(encoding='utf-8').replace('common031','common036').replace('api031','api036')
s=s[:s.index('def auxiliary_jobs():')]
s=s.replace('031','036')
s=s.replace("body=a.body(item['text'],ref,'score');jobs.append(dict(request_id='036_score_'+pid,proposition_id=pid,kind='chat',role='score',body=body))", "\n        for round_name in (['R0','R1'] if item['subject_id'] in c.read(c.OUT/'final_freeze_001/config.json')['repeat_patients'] else ['R0']):\n            for role in ('baseline','score'):\n                jobs.append(dict(request_id='036_'+round_name+'_'+role+'_'+pid,round=round_name,proposition_id=pid,kind='chat',role=role,body=a.body(item['text'],ref,role)))")
save('retrieval036.py',s)
print('Created task-owned API/C48 modules; original031 files untouched.')
