"""Build reranker pair IDs for an embedding variant; no GT/Judge metrics."""
from pathlib import Path
import argparse, json
import common021 as c

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tag',required=True);a=ap.parse_args()
    candidates={x['proposition_id']:x for x in c.jsonlines(c.OUT/f'local_candidates_{a.tag}.jsonl')}
    api_jobs={x['proposition_id']:x for x in c.jsonlines(c.CAN20/'jobs.jsonl')}
    rows=[]
    for pid in sorted(candidates):
        local=candidates[pid]['local_C48']; api_union=api_jobs[pid]['passage_ids']
        score_ids=sorted(set(api_union)|set(local))
        rows.append({'proposition_id':pid,'score_ids':score_ids})
    out=c.OUT/f'rerank_pair_ids_{a.tag}.jsonl'
    with out.open('w',encoding='utf-8',newline='\n') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n')
    c.save(c.OUT/f'rerank_pair_{a.tag}_summary.json',{'tag':a.tag,'claims':len(rows),'pairs':sum(len(x['score_ids']) for x in rows),'api_pairs':sum(len(api_jobs[x['proposition_id']]['passage_ids']) for x in rows),'local_extra_pairs':sum(len(set(candidates[x['proposition_id']]['local_C48'])-set(api_jobs[x['proposition_id']]['passage_ids'])) for x in rows)})
    print(json.dumps(c.read(c.OUT/f'rerank_pair_{a.tag}_summary.json')),flush=True)
if __name__=='__main__':main()
