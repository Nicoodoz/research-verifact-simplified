"""Construct the original C48 with receipted embeddings/reranking, then four fixed bodies."""
from pathlib import Path
import argparse
import numpy as np
import common016 as c
from io016 import load_phase

def candidates(phase):
    c.patient_ids(phase);prep=c.OUT/phase/'preparation_001';c.check_manifest(prep)
    values,_=load_phase(phase+'_embedding');vectors={}
    for v in values.values():
        c.require(v['status']=='received' and v['native']['model']==c.baseline.EMBED_MODEL,'Missing/wrong embedding')
        j=v['job'];data=v['native']['data'];c.require(sorted(x['index'] for x in data)==list(range(len(j['text_ids']))),'Embedding index set')
        for x in data:
            key=j['text_ids'][x['index']];a=np.asarray(x['embedding'],dtype=np.float64)
            c.require(key not in vectors and a.shape==(1024,) and np.isfinite(a).all() and np.linalg.norm(a)>0,'Invalid embedding vector')
            vectors[key]=a
    corpus=c.jsonlines(prep/'corpus.jsonl');inputs=c.jsonlines(prep/'inputs.jsonl');catalog=c.read(prep/'embedding_catalog.json')
    c.require(set(vectors)==set(catalog),'Incomplete embedding catalog')
    passages={p['passage_id']:p for p in corpus}
    indices={sid:c.baseline.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in sorted({p['subject_id'] for p in corpus}) for pp in [[p for p in corpus if p['subject_id']==sid]]}
    records=[];jobs=[]
    for item in inputs:
        ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']]) if item['subject_id'] in indices else dict(bm25=[],dense=[],hybrid=[])
        pools={a+'48':c.baseline.candidates(ranks,a) for a in ('A','B','C')};union=sorted({pid for pool in pools.values() for pid in pool})
        docs=[passages[pid]['search_text'] for pid in union]
        c.require(all(len((item['text']+t).encode())<8192 for t in docs),'Original reranker pair limit')
        if union:jobs.append(dict(request_id=phase+':rerank:'+item['proposition_id'],kind='rerank',proposition_id=item['proposition_id'],passage_ids=union,
            body=dict(model=c.baseline.RERANK_MODEL,query=item['text'],documents=docs,top_n=len(union),return_documents=False,max_chunks_per_doc=1)))
        records.append(dict(proposition_id=item['proposition_id'],rankings=ranks,candidate_ids=pools))
    jobs.sort(key=lambda j:c.hash_rank(j['request_id'],'016/rerank/v1:'))
    out=c.OUT/phase/'candidates_001';c.require(not out.exists(),'Candidates exist');out.mkdir()
    c.write_lines(out/'candidates.jsonl',records);c.write_lines(out/'jobs.jsonl',jobs)
    keys=sorted(vectors);c.write_json(out/'embedding_ids.json',keys);np.save(out/'vectors.npy',np.asarray([vectors[k] for k in keys]),allow_pickle=False)
    c.write_json(out/'summary.json',dict(claims=len(inputs),rerank_requests=len(jobs),pairs=sum(len(j['passage_ids']) for j in jobs),
        single_attempt_rerank_reservations=sum(c.bound(j) for j in jobs),C48_only_final_reference=True,legacy_union_rerank_preserved=True))
    c.seal(out,[prep/'manifest.json',c.OUT/'live'/f'{phase}_embedding'/'manifest.json'],[Path(__file__),c.TASK/'io016.py',c.TASK/'common016.py'])
    print(c.canonical(c.read(out/'summary.json')))

def judge(phase):
    c.patient_ids(phase);root=c.OUT/phase;prep=root/'preparation_001';can=root/'candidates_001'
    c.check_manifest(prep);c.check_manifest(can);values,_=load_phase(phase+'_rerank')
    inputs=c.jsonlines(prep/'inputs.jsonl');candidate={r['proposition_id']:r for r in c.jsonlines(can/'candidates.jsonl')}
    passages={r['passage_id']:r for r in c.jsonlines(prep/'corpus.jsonl')};prompts=c.read(prep/'judge_prompts.json')
    records=[];assignments=[];jobs={}
    for item in inputs:
        pid=item['proposition_id'];pools=candidate[pid]['candidate_ids'];union=sorted({p for pool in pools.values() for p in pool});scores={}
        if union:
            v=values[phase+':rerank:'+pid];c.require(v['status']=='received','Missing rerank')
            native=v['native'];c.require(native.get('model',c.baseline.RERANK_MODEL)==c.baseline.RERANK_MODEL,'Wrong rerank model')
            rr=native['results'];c.require(sorted(x['index'] for x in rr)==list(range(len(union))),'Incomplete rerank indices')
            scores={union[x['index']]:float(x['relevance_score']) for x in rr};c.require(all(np.isfinite(x) for x in scores.values()),'Bad score')
        packed=c.baseline.core.select_evidence(pools['C48'],scores,passages,item['admission'])
        records.append(dict(item,**packed,candidate_ids=pools['C48'],scores=scores))
        for role in c.ROLES:
            body=c.judge_body(item,packed['reference'],prompts,role);sha=c.fingerprint(body)
            rid=f'016:{phase}:{role}:{sha}'
            jobs.setdefault(rid,dict(request_id=rid,kind='chat',role=role,proposition_id=pid,case_id=item['case_id'],body=body))
            assignments.append(dict(proposition_id=pid,case_id=item['case_id'],role=role,request_id=rid,body_sha256=sha))
    ordered=sorted(jobs.values(),key=lambda j:c.hash_rank(j['request_id'],'016/send/v1:'))
    out=root/'judge_preparation_001';c.require(not out.exists(),'Judge prep exists');out.mkdir()
    c.write_lines(out/'inputs.jsonl',records);c.write_lines(out/'jobs.jsonl',ordered);c.write_csv(out/'assignments.csv',assignments)
    estimates={role:sum((sum(len(m['content']) for m in j['body']['messages'])*.4*3+(450 if role=='qwen' else 350)*(12 if role=='qwen' else 9))/1e6
        for j in ordered if j['role']==role) for role in c.ROLES}
    c.write_json(out/'summary.json',dict(claims=len(inputs),logical_calls=len(assignments),actual_distinct_role_calls=len(ordered),
        within_role_saved_calls=len(assignments)-len(ordered),V1_V2_same_body_but_fresh_calls=True,
        by_role_estimated_peak_cny=estimates,estimated_peak_cny=sum(estimates.values()),
        single_attempt_byte_reservations=sum(c.bound(j) for j in ordered),reference_sha256={r['proposition_id']:c.pilot.digest_text(r['reference']) for r in records}))
    c.seal(out,[prep/'manifest.json',can/'manifest.json',c.OUT/'live'/f'{phase}_rerank'/'manifest.json'],[Path(__file__),c.TASK/'common016.py',c.TASK/'io016.py'])
    print(c.canonical({k:v for k,v in c.read(out/'summary.json').items() if k!='reference_sha256'}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('candidates','judge'));p.add_argument('phase',choices=('stage1','confirmation'))
    a=p.parse_args();globals()[a.stage](a.phase)
