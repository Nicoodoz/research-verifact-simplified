"""Prepare fixed raw-EHR corpus, verified C48 caches and whole-task cost forecast."""
import json,sys,math
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
import common031 as c
sys.path.insert(0,str(c.ROOT/'tasks/028_traceable_claim_evidence_verification'))
import common028 as old28
b=old28.api.old.baseline

def verify_file(path,manifest):
    m=c.read(manifest);target=path.relative_to(c.ROOT).as_posix();found=[]
    for section in ('sha256','files','dependencies','outputs'):
        for key,h in m.get(section,{}).items():
            if key==target or (manifest.parent/key).resolve()==path.resolve():found.append(h)
    c.require(found and all(c.sha(path)==h for h in found),'Source file hash not bound '+str(path))

def run():
    out=c.OUT/'materials_001';c.require(not out.exists(),'Material preparation exists');meta=c.csvread(c.OUT/'planning_001/claim_metadata.csv');subjects={r['subject_id'] for r in meta};raw=b.RAW;sources=[]
    # Select only scoped patients/fields. No label/source-BHC columns are queried.
    import duckdb
    con=duckdb.connect();ids=pd.DataFrame({'sid':sorted(subjects)});con.register('scope_ids',ids)
    def scoped(path,subjectcol,columns='*'):
        sources.append(path);return con.execute(f'SELECT {columns} FROM read_csv(?,all_varchar=true) t WHERE CAST(t."{subjectcol}" AS BIGINT)::VARCHAR IN (SELECT sid FROM scope_ids)',[str(path)]).df().fillna('').to_dict('records')
    props=scoped(raw/'propositions/propositions.csv.gz','subject_id','t.proposition_id,t.subject_id,t.hadm_id,t.text');props={r['proposition_id']:r for r in props}
    admissions={str(int(r['SUBJECT_ID'])):r for r in scoped(raw/'reference_ehr/admissions.csv.gz','SUBJECT_ID')};notes=scoped(raw/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID')
    inputs=[]
    for r in meta:
        p=props[r['proposition_id']];c.require(str(int(p['subject_id']))==r['subject_id'] and str(int(p['hadm_id']))==r['hadm_id'],'Claim identity')
        inputs.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],role=r['role'],author_type=r['author_type'],text=p['text'],admission=admissions[r['subject_id']],claim_embedding_id=b.pilot.digest_text(p['text'])))
    corpus=[]
    for note in sorted(notes,key=lambda n:int(n['ROW_ID'])):
        sid=str(int(note['SUBJECT_ID']));ad=admissions[sid];date=note['CHARTDATE'][:10]
        if not date or not ad['ADMITTIME'][:10]<=date<=ad['DISCHTIME'][:10] or note['CATEGORY'].strip().lower()=='discharge summary':continue
        for lo,hi in b.core.paragraph_spans(note['TEXT']):
            p=dict(subject_id=sid,note_id=note['ROW_ID'],hadm_id=note['HADM_ID'],date=date,time=note['CHARTTIME'][11:] or 'Unknown',category=note['CATEGORY'],description=note['DESCRIPTION'],start=lo,end_exclusive=hi,text=note['TEXT'][lo:hi],note_sha256=b.pilot.digest_text(note['TEXT']));p['passage_id']=b.prior.fingerprint(p) if hasattr(b.prior,'fingerprint') else old28.api.fingerprint(p);p['search_text']=f"Date: {p['date']}. {p['category']} {p['description']}. {p['text']}";p['embedding_id']=b.pilot.digest_text(p['search_text']);corpus.append(p)
    corpus.sort(key=lambda p:p['passage_id']);by_passage={p['passage_id']:p for p in corpus};byclaim={p['proposition_id']:p for p in inputs};cached=[]
    paths=[(c.ROOT/'outputs/009_retrieval_baselines/development_001/judge_preparation/inputs.jsonl','009'),(c.ROOT/'outputs/016_disagreement_triggered_review_validation/stage1/base_preparation_001/inputs.jsonl','016')]
    for path,kind in paths:
        verify_file(path,path.parent/'manifest.json');sources.extend([path,path.parent/'manifest.json'])
        for r in c.lines(path):
            pid=r['proposition_id']
            if pid not in byclaim:continue
            x=byclaim[pid];record=r['retrieval']['C48'] if kind=='009' else r;c.require(r['text']==x['text'],'Cached claim differs');selected=b.core.select_evidence(record['candidate_ids'],r['scores'],by_passage,x['admission']);c.require(selected['reference']==record['reference'],'Cached C48 reconstruction differs')
            cached.append(dict(proposition_id=pid,reference=record['reference'],source=path.relative_to(c.ROOT).as_posix(),reference_sha256=b.pilot.digest_text(record['reference'])))
    cached_byid={r['proposition_id']:r for r in cached};c.require(len(cached_byid)==len(cached),'Duplicate cached C48')
    missing=[r for r in inputs if r['proposition_id'] not in cached_byid];needed_subjects={r['subject_id'] for r in missing};catalog={p['embedding_id']:p['search_text'] for p in corpus if p['subject_id'] in needed_subjects};catalog.update({r['claim_embedding_id']:r['text'] for r in missing});vectors={};vector_sources={}
    for base,idsname,vecname in [(c.ROOT/'outputs/008_retrieval_planning/candidates_001','embedding_ids.json','embedding_vectors.npy'),(c.ROOT/'outputs/016_disagreement_triggered_review_validation/stage1/candidates_001','embedding_ids.json','vectors.npy')]:
        ip=base/idsname;vp=base/vecname;verify_file(ip,base/'manifest.json');verify_file(vp,base/'manifest.json');sources.extend([ip,vp,base/'manifest.json']);keys=c.read(ip);vv=np.load(vp,allow_pickle=False,mmap_mode='r');c.require(len(keys)==len(vv),'Vector identity count')
        for key,row in zip(keys,vv):
            if key in catalog and key not in vectors:vectors[key]=np.asarray(row,dtype=float);vector_sources[key]=vp.relative_to(c.ROOT).as_posix()
    pending={k:v for k,v in catalog.items() if k not in vectors};embedjobs=old28.api.old.embedding_jobs(pending,'031_embed');c.require(all(0<len(t.encode())<8192 for t in catalog.values()),'Embedding bound')
    # Price estimation uses old usage only, never new candidate counts/labels/performance.
    norm=c.lines(c.ROOT/'outputs/026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl');oldusage={role:[r['usage'] for r in norm if r['arm']=='S' and r['model_key']==role] for role in ('deepseek','qwen')};n28=c.lines(c.ROOT/'outputs/028_traceable_claim_evidence_verification/analysis_001/normalized.jsonl')
    mean_cost={role:float(np.mean([(u['prompt_tokens']*3+u['completion_tokens']*(9 if role=='deepseek' else 12))/1e6 for u in us])) for role,us in oldusage.items()}
    for role in ('repeat','trace'):mean_cost[role]=float(np.mean([(r['usage']['prompt_tokens']*3+r['usage']['completion_tokens']*9)/1e6 for r in n28 if r['arm']==role]))
    missingids=[r['proposition_id'] for r in missing];maxrerank=96;retrieval_bound=sum(b.native.bound(j) for j in embedjobs)+sum((maxrerank*(len(r['text'].encode())+750+256)+2000)*.07/1e6 for r in missing)
    n=len(inputs);candidate_fraction=.25;expected=n*mean_cost['deepseek']+math.ceil(n*candidate_fraction)*sum(mean_cost[k] for k in ('qwen','repeat','trace'))+retrieval_bound;margin=expected*1.3+3
    out.mkdir(parents=True);c.jsonl(out/'inputs.jsonl',inputs);c.jsonl(out/'corpus.jsonl',corpus);c.jsonl(out/'cached_c48.jsonl',cached);c.jsonl(out/'embedding_jobs.jsonl',embedjobs);c.put(out/'embedding_catalog.json',catalog);keys=sorted(vectors);c.put(out/'embedding_ids.json',keys);np.save(out/'vectors.npy',np.array([vectors[k] for k in keys]),allow_pickle=False);c.put(out/'vector_sources.json',vector_sources)
    budget=dict(new_claims=n,cached_C48=len(cached),missing_C48=len(missing),corpus_passages=len(corpus),embedding_texts=len(catalog),cached_embedding_texts=len(vectors),new_embedding_requests=len(embedjobs),historical_mean_role_cny=mean_cost,planning_candidate_rate=candidate_fraction,historical_rate=155/1529,retrieval_conservative_cny=retrieval_bound,expected_cny=expected,expected_plus30pct_plus3reserve=margin,cap_cny=80,feasible=margin<=80,assumptions='25% new candidates vs old10.14%; roles use audited usage means; 30% overhead and3CNY reserve; peak/no-cache prices; no new service answers yet',prices={'deepseek':[3,9],'qwen':[3,12],'Pro_BGE':.07},new_API_calls=0,confirmation_GT_read=False)
    c.put(out/'budget.json',budget);c.put(out/'manifest.json',dict(created_utc=c.now(),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sources+[c.OUT/'planning_001/manifest.json']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print(json.dumps(budget,ensure_ascii=False))
if __name__=='__main__':run()
