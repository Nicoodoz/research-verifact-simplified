"""Resumeable fixed C48 and GT-blind role outputs; no confirmation labels."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json
import numpy as np
import common036 as c
import api036 as a
b=a.api.old.baseline

def seal(folder,rows,name='jobs.jsonl'):
    c.require(not folder.exists(),'Do not overwrite phase');folder.mkdir(parents=True);c.jsonl(folder/name,rows);c.put(folder/'manifest.json',dict(created_utc=c.now(),file=name,sha256=c.sha(folder/name)))
def verify_execution():
    for p,h in c.read(c.OUT/'execution_freeze_001.json')['sha256'].items():c.require(c.sha(c.ROOT/p)==h,'Execution code/input changed '+p)
def candidates():
    folder=c.OUT/'retrieval_001'
    if folder.exists():return c.lines(folder/'jobs.jsonl')
    mat=c.OUT/'materials_001';cached={r['proposition_id'] for r in c.lines(mat/'cached_c48.jsonl')};inputs=[r for r in c.lines(mat/'inputs.jsonl') if r['proposition_id'] not in cached];corpus=c.lines(mat/'corpus.jsonl');catalog=c.read(mat/'embedding_catalog.json');keys=c.read(mat/'embedding_ids.json');vectors=dict(zip(keys,np.load(mat/'vectors.npy',allow_pickle=False)));_,term,_=a.state()
    for job in c.lines(mat/'embedding_jobs.jsonl'):
        r=term.get(job['request_id']);c.require(r is not None and r['parsed']['status']=='success','Embedding missing/invalid; do not substitute')
        native=json.loads(r['transport']['body_text'])
        for z in native['data']:vectors[job['text_ids'][z['index']]]=np.asarray(z['embedding'],float)
    c.require(set(vectors)==set(catalog),'Incomplete embedding catalog');passages={p['passage_id']:p for p in corpus};needed={r['subject_id'] for r in inputs};indices={sid:b.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in sorted(needed) for pp in [[p for p in corpus if p['subject_id']==sid]]};records=[];jobs=[]
    for item in inputs:
        ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']]);pools={x+'48':b.candidates(ranks,x) for x in ('A','B','C')};union=sorted({p for pool in pools.values() for p in pool});docs=[passages[p]['search_text'] for p in union];c.require(len(union)<=120 and all(len((item['text']+d).encode())<8192 for d in docs),'Rerank bounds')
        if union:jobs.append(dict(request_id='036_rerank_'+item['proposition_id'],kind='rerank',proposition_id=item['proposition_id'],passage_ids=union,body=dict(model=b.RERANK_MODEL,query=item['text'],documents=docs,top_n=len(union),return_documents=False,max_chunks_per_doc=1)))
        records.append(dict(proposition_id=item['proposition_id'],rankings=ranks,candidate_ids=pools))
    jobs.sort(key=lambda j:c.digest(['036_rerank_order',j['request_id']]));seal(folder,jobs);c.jsonl(folder/'candidates.jsonl',records);c.put(folder/'details.json',dict(claims=len(inputs),requests=len(jobs),pairs=sum(len(j['passage_ids']) for j in jobs),candidate_sha256=c.sha(folder/'candidates.jsonl'),built_from_API_only=True));return jobs
def score_jobs():
    out=c.OUT/'judge_inputs_001'
    if out.exists():return c.lines(out/'jobs.jsonl')
    mat=c.OUT/'materials_001';cached={r['proposition_id']:r for r in c.lines(mat/'cached_c48.jsonl')};ins=c.lines(mat/'inputs.jsonl');passages={r['passage_id']:r for r in c.lines(mat/'corpus.jsonl')};cans={r['proposition_id']:r for r in c.lines(c.OUT/'retrieval_001/candidates.jsonl')};_,term,_=a.state();materials=[];jobs=[]
    for item in ins:
        pid=item['proposition_id']
        if pid in cached:ref=cached[pid]['reference'];selected=None;source=cached[pid]['source']
        else:
            pools=cans[pid]['candidate_ids'];union=sorted({p for pool in pools.values() for p in pool});scores={}
            if union:
                r=term.get('036_rerank_'+pid);c.require(r is not None and r['parsed']['status']=='success','Rerank missing/invalid');response=json.loads(r['transport']['body_text']);scores={union[x['index']]:float(x['relevance_score']) for x in response['results']}
            packed=b.core.select_evidence(pools['C48'],scores,passages,item['admission']);ref=packed['reference'];selected=packed['selected_ids'];source='036_API_BGE_C48'
        materials.append(dict(proposition_id=pid,subject_id=item['subject_id'],role=item['role'],author_type=item['author_type'],text=item['text'],reference=ref,reference_sha256=b.pilot.digest_text(ref),selected_ids=selected,evidence_source=source));
        for round_name in (['R0','R1'] if item['subject_id'] in c.read(c.OUT/'final_freeze_001/config.json')['repeat_patients'] else ['R0']):
            for role in ('baseline','score'):
                jobs.append(dict(request_id='036_'+round_name+'_'+role+'_'+pid,round=round_name,proposition_id=pid,kind='chat',role=role,body=a.body(item['text'],ref,role)))
    jobs.sort(key=lambda j:c.digest(['036_send_score',j['request_id']]));seal(out,jobs);c.jsonl(out/'materials.jsonl',materials);c.put(out/'evidence_freeze.json',dict(created_utc=c.now(),materials_sha256=c.sha(out/'materials.jsonl'),no_GT_in_input=True,claims=len(ins)));return jobs
