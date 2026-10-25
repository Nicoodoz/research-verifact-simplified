"""Resumeable fixed C48 and GT-blind role outputs; no confirmation labels."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import argparse,json
import numpy as np
import common031 as c
import api031 as a
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
        if union:jobs.append(dict(request_id='031_rerank_'+item['proposition_id'],kind='rerank',proposition_id=item['proposition_id'],passage_ids=union,body=dict(model=b.RERANK_MODEL,query=item['text'],documents=docs,top_n=len(union),return_documents=False,max_chunks_per_doc=1)))
        records.append(dict(proposition_id=item['proposition_id'],rankings=ranks,candidate_ids=pools))
    jobs.sort(key=lambda j:c.digest(['031_rerank_order',j['request_id']]));seal(folder,jobs);c.jsonl(folder/'candidates.jsonl',records);c.put(folder/'details.json',dict(claims=len(inputs),requests=len(jobs),pairs=sum(len(j['passage_ids']) for j in jobs),candidate_sha256=c.sha(folder/'candidates.jsonl'),built_from_API_only=True));return jobs
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
                r=term.get('031_rerank_'+pid);c.require(r is not None and r['parsed']['status']=='success','Rerank missing/invalid');response=json.loads(r['transport']['body_text']);scores={union[x['index']]:float(x['relevance_score']) for x in response['results']}
            packed=b.core.select_evidence(pools['C48'],scores,passages,item['admission']);ref=packed['reference'];selected=packed['selected_ids'];source='031_API_BGE_C48'
        materials.append(dict(proposition_id=pid,subject_id=item['subject_id'],role=item['role'],author_type=item['author_type'],text=item['text'],reference=ref,reference_sha256=b.pilot.digest_text(ref),selected_ids=selected,evidence_source=source));body=a.body(item['text'],ref,'score');jobs.append(dict(request_id='031_score_'+pid,proposition_id=pid,kind='chat',role='score',body=body))
    jobs.sort(key=lambda j:c.digest(['031_send_score',j['request_id']]));seal(out,jobs);c.jsonl(out/'materials.jsonl',materials);c.put(out/'evidence_freeze.json',dict(created_utc=c.now(),materials_sha256=c.sha(out/'materials.jsonl'),no_GT_in_input=True,claims=len(ins)));return jobs
def auxiliary_jobs():
    out=c.OUT/'candidate_freeze_001'
    if out.exists():return c.lines(out/'jobs.jsonl')
    materials=c.lines(c.OUT/'judge_inputs_001/materials.jsonl');_,term,_=a.state();ledger=[];jobs=[]
    for r in materials:
        response=term.get('031_score_'+r['proposition_id']);p=response['parsed'] if response else dict(status='missing');candidate=False;u0=u2=None
        if p['status'] in a.api.VALID:
            scores=p['scores'];u0=int(c.base.old.decode(c.base.old.logs(scores),0));u2=int(c.base.old.decode(c.base.old.logs(scores),2));candidate=u0!=0 and u2==0
        ledger.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],group=r['role'],score_status=p['status'],u0=u0,u2=u2,candidate=candidate))
        if candidate:
            for role in ('peer','repeat','trace'):jobs.append(dict(request_id='031_'+role+'_'+r['proposition_id'],proposition_id=r['proposition_id'],kind='chat',role=role,body=a.body(r['text'],r['reference'],role)))
    jobs.sort(key=lambda j:c.digest(['031_send_aux',j['request_id']]));seal(out,jobs);c.jsonl(out/'candidates.jsonl',ledger);c.put(out/'summary.json',dict(created_utc=c.now(),claims=len(ledger),candidates=sum(r['candidate'] for r in ledger),score_invalid=sum(r['u0'] is None for r in ledger),requests=len(jobs),GT_read=False,candidate_ledger_sha256=c.sha(out/'candidates.jsonl')));return jobs
def main(stage):
    verify_execution()
    if stage=='embedding':jobs=c.lines(c.OUT/'materials_001/embedding_jobs.jsonl');workers=4
    elif stage=='rerank':jobs=candidates();workers=4
    elif stage=='score':jobs=score_jobs();workers=12
    else:jobs=auxiliary_jobs();workers=12
    attempts,_,_=a.state();used=sum(r['charge_cny'] for r in attempts);m=c.read(c.OUT/'freeze_001/budget_002.json')['mean_role_cost_cny'];_,terminal,_=a.state();todo=[j for j in jobs if j['request_id'] not in terminal]
    # Remaining-task forecast before stages, plus request-level conservative reservations.
    estimated=used+sum(a.bound(j) if j['kind']!='chat' else m['qwen' if j['role']=='peer' else 'deepseek' if j['role']=='score' else j['role']] for j in todo)
    if stage=='score':estimated+=len(todo)*.25*sum(m[r] for r in ('qwen','repeat','trace'))
    c.require(estimated+3<=80,'Remaining task forecast exceeds80; no shrinking confirmation')
    print(stage,'jobs',len(jobs),'remaining',len(todo),'forecast+reserve',estimated+3,flush=True);a.run(jobs,stage,workers)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('embedding','rerank','score','auxiliary'));main(p.parse_args().stage)
