"""Candidate reconstruction for precision diagnostics; no GT/Judge metrics."""
from pathlib import Path
import argparse, json, sys
import numpy as np
import common021 as c
sys.path.insert(0,str(c.ROOT/'tasks/009_retrieval_baselines'))
import study009 as baseline

def write_jsonl(path,rows):
    with Path(path).open('w',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--vectors',required=True);ap.add_argument('--tag',required=True);a=ap.parse_args()
    ids=c.read(c.CAN20/'embedding_ids.json')
    arr=np.load(c.OUT/a.vectors,allow_pickle=False)
    vectors={k:arr[i].astype(np.float64) for i,k in enumerate(ids)}
    corpus=c.jsonlines(c.PREP20/'corpus.jsonl');inputs=c.jsonlines(c.PREP20/'inputs.jsonl')
    api={x['proposition_id']:x for x in c.jsonlines(c.CAN20/'candidates.jsonl')}
    passages={p['passage_id']:p for p in corpus}
    indices={}
    for sid in sorted({p['subject_id'] for p in corpus}):
        pp=[p for p in corpus if p['subject_id']==sid]
        indices[sid]=baseline.core.HybridIndex(pp,[vectors[p['embedding_id']] for p in pp])
    rows=[]
    for item in inputs:
        ranks=indices[item['subject_id']].retrieve(item['text'],vectors[item['claim_embedding_id']])
        pools={x+'48':baseline.candidates(ranks,x) for x in ('A','B','C')}
        old=api[item['proposition_id']]['candidate_ids']
        rows.append({'proposition_id':item['proposition_id'],'api_B48':old['B48'],'api_C48':old['C48'],'local_B48':pools['B48'],'local_C48':pools['C48']})
    write_jsonl(c.OUT/f'local_candidates_{a.tag}.jsonl',rows)
    summary={
        'tag':a.tag,'claims':len(rows),
        'B48_order_exact':sum(x['api_B48']==x['local_B48'] for x in rows),
        'B48_set_exact':sum(set(x['api_B48'])==set(x['local_B48']) for x in rows),
        'C48_order_exact':sum(x['api_C48']==x['local_C48'] for x in rows),
        'C48_set_exact':sum(set(x['api_C48'])==set(x['local_C48']) for x in rows),
        'B48_jaccard_mean':float(np.mean([len(set(x['api_B48'])&set(x['local_B48']))/len(set(x['api_B48'])|set(x['local_B48'])) for x in rows])),
        'C48_jaccard_mean':float(np.mean([len(set(x['api_C48'])&set(x['local_C48']))/len(set(x['api_C48'])|set(x['local_C48'])) for x in rows])),
    }
    c.save(c.OUT/f'candidate_{a.tag}_summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
