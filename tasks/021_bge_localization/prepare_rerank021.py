"""Rebuild 020 dense/C48 candidates with local vectors; no model calls."""
from pathlib import Path
import sys, json
import numpy as np
import common021 as c

sys.path.insert(0,str(c.ROOT/'tasks/009_retrieval_baselines'))
import study009 as baseline

def write_jsonl(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='\n') as f:
        for row in rows:
            f.write(json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')

def main():
    ids=c.read(c.OUT/'local_embedding_ids.json')
    local=np.load(c.OUT/'local_vectors_fp16.npy',allow_pickle=False)
    if local.shape!=(len(ids),1024): raise ValueError('Local vector shape')
    vectors={k:local[i].astype(np.float64) for i,k in enumerate(ids)}
    corpus=c.jsonlines(c.PREP20/'corpus.jsonl')
    inputs=c.jsonlines(c.PREP20/'inputs.jsonl')
    api_candidates={x['proposition_id']:x for x in c.jsonlines(c.CAN20/'candidates.jsonl')}
    api_jobs={x['proposition_id']:x for x in c.jsonlines(c.CAN20/'jobs.jsonl')}

    passages={p['passage_id']:p for p in corpus}
    subjects=sorted({p['subject_id'] for p in corpus})
    indices={}
    for sid in subjects:
        pp=[p for p in corpus if p['subject_id']==sid]
        indices[sid]=baseline.core.HybridIndex(
            pp,[vectors[p['embedding_id']] for p in pp]
        )
    records=[]; pairsets=[]
    for n,item in enumerate(inputs,1):
        pid=item['proposition_id']
        ranks=indices[item['subject_id']].retrieve(
            item['text'],vectors[item['claim_embedding_id']]
        )
        pools={a+'48':baseline.candidates(ranks,a) for a in ('A','B','C')}
        api=api_candidates[pid]['candidate_ids']
        api_union=api_jobs[pid]['passage_ids']
        score_ids=sorted(set(api_union)|set(pools['C48']))
        if not set(score_ids)<=set(passages): raise ValueError('Unknown passage')
        records.append({
            'proposition_id':pid,
            'api_B48':api['B48'],'api_C48':api['C48'],
            'local_B48':pools['B48'],'local_C48':pools['C48'],
            'api_union_ids':api_union,'score_ids':score_ids,
        })

        pairsets.append({
            'proposition_id':pid,
            'query_embedding_id':item['claim_embedding_id'],
            'score_ids':score_ids,
        })
        if n%100==0: print(f'CANDIDATES {n}/{len(inputs)}',flush=True)
    c.OUT.mkdir(parents=True,exist_ok=True)
    write_jsonl(c.OUT/'local_candidates.jsonl',records)
    write_jsonl(c.OUT/'rerank_pair_ids.jsonl',pairsets)
    summary={
        'claims':len(records),
        'pair_count':sum(len(x['score_ids']) for x in pairsets),
        'api_B48_exact':sum(x['api_B48']==x['local_B48'] for x in records),
        'api_C48_exact':sum(x['api_C48']==x['local_C48'] for x in records),
        'local_only_pairs':sum(len(set(x['local_C48'])-set(x['api_union_ids'])) for x in records),
    }
    c.save(c.OUT/'candidate_local_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
