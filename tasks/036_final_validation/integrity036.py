"""Offline full C48 and actual request alignment replay before reserved evaluation."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[key]='1'
import json,argparse
from pathlib import Path
import numpy as np
import common036 as c
import api036 as a
import execute036 as e
b=a.api.old.baseline
def main(output=None):
    out=Path(output).resolve() if output else c.OUT/'integrity_001'
    if output:assert out.is_relative_to(c.ROOT/'outputs/replays')
    assert not out.exists();c.base.offline();e.verify_freeze()
    for path,h in c.read(c.OUT/'published_baseline_sources_001.json')['sha256'].items():assert c.sha(c.ROOT/path)==h
    for path,h in c.read(c.OUT/'evaluation_freeze_001/manifest.json')['sha256'].items():assert c.sha(c.ROOT/path)==h
    attempts,term,_=a.state();mat=c.OUT/'materials_001';corpus=c.lines(mat/'corpus.jsonl');passages={p['passage_id']:p for p in corpus};raw={p['proposition_id']:p for p in c.lines(mat/'inputs.jsonl')};keys=c.read(mat/'embedding_ids.json');vectors=dict(zip(keys,np.load(mat/'vectors.npy',allow_pickle=False)))
    for j in c.lines(mat/'embedding_jobs.jsonl'):
        r=term[j['request_id']];assert r['parsed']['status']=='success'
        for z in json.loads(r['transport']['body_text'])['data']:vectors[j['text_ids'][z['index']]]=np.asarray(z['embedding'],float)
    assert set(vectors)==set(c.read(mat/'embedding_catalog.json'))
    indices={sid:b.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp]) for sid in sorted(set(p['subject_id'] for p in raw.values())) for pp in [[p for p in corpus if p['subject_id']==sid]]}
    cans={r['proposition_id']:r for r in c.lines(c.OUT/'retrieval_001/candidates.jsonl')};materials=c.lines(c.OUT/'judge_inputs_001/materials.jsonl');lookup={r['proposition_id']:r for r in materials};checked=[]
    for r in materials:
        pid=r['proposition_id'];item=raw[pid];ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']]);pools={x+'48':b.candidates(ranks,x) for x in ('A','B','C')};assert pools==cans[pid]['candidate_ids']
        union=sorted({p for pool in pools.values() for p in pool});scores={}
        if union:
            result=term['036_rerank_'+pid];assert result['parsed']['status']=='success';rr=json.loads(result['transport']['body_text']);scores={union[x['index']]:float(x['relevance_score']) for x in rr['results']}
        selection=b.core.select_evidence(pools['C48'],scores,passages,item['admission']);assert selection['reference']==r['reference'] and selection['selected_ids']==r['selected_ids'];assert selection['body_characters']<=8000 and len(selection['selected_ids'])<=16
        reference_hash=b.pilot.digest_text(r['reference']);assert reference_hash==r['reference_sha256']
        checked.append(dict(id=pid,reference_sha256=reference_hash,selected_n=len(selection['selected_ids']),body_characters=selection['body_characters']))
    config=c.read(c.OUT/'final_freeze_001/config.json');expected={(rn,role,r['proposition_id']) for r in materials for rn in (['R0','R1'] if r['subject_id'] in config['repeat_patients'] else ['R0']) for role in ('baseline','score')}
    jobs=c.lines(c.OUT/'judge_inputs_001/jobs.jsonl');assert {(j['round'],j['role'],j['proposition_id']) for j in jobs}==expected
    alljobs=jobs+c.lines(c.OUT/'candidate_freeze_001/jobs.jsonl')
    for j in alljobs:
        r=lookup[j['proposition_id']];assert j['body']==a.body(r['text'],r['reference'],j['role']);payload=json.loads(j['body']['messages'][1]['content']);assert set(payload)=={'proposition','reference'}
    candidates=c.lines(c.OUT/'candidate_freeze_001/candidates.jsonl');aux={(j['round'],j['proposition_id']) for j in alljobs if j['role']=='peer'};assert aux=={(r['round'],r['proposition_id']) for r in candidates if r['candidate']}
    for r in candidates:
        t=term.get('036_'+r['round']+'_score_'+r['proposition_id'],{}).get('parsed',{})
        if t.get('status') in a.api.VALID:
            z=c.base.old.logs(t['scores']);u0=int(c.base.old.decode(z,0));u2=int(c.base.old.decode(z,2));assert r['u0']==u0 and r['u2']==u2 and r['candidate']==(u0!=0 and u2==0)
        else:assert r['u0'] is None and not r['candidate']
    c.csvwrite(out/'references_replayed.csv',checked);c.put(out/'summary.json',dict(created_utc=c.now(),status='PASS',all_C48_reconstructed=len(checked),all_actual_Judge_bodies_checked=len(alljobs),candidate_only_peer_requests=len(aux),GT_read=False,new_API=0,attempts=len(attempts),cost_used_or_reserved=sum(x['charge_cny'] for x in attempts)));print('036 full C48/input replay PASS',len(checked),len(alljobs),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output');main(parser.parse_args().output)
