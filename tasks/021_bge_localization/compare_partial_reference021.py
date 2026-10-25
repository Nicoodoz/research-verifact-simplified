"""Partial final-reference equivalence on completed local reranker rows; no GT/Judge metrics."""
import argparse, json, sys
import numpy as np
import common021 as c
sys.path.insert(0,str(c.ROOT/'tasks/009_retrieval_baselines'))
import study009 as baseline

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--scores',required=True); ap.add_argument('--candidates',required=True); a=ap.parse_args()
    base={x['proposition_id']:x for x in c.jsonlines(c.BASE20/'inputs.jsonl')}
    prep={x['proposition_id']:x for x in c.jsonlines(c.PREP20/'inputs.jsonl')}
    passages={x['passage_id']:x for x in c.jsonlines(c.PREP20/'corpus.jsonl')}
    cans={x['proposition_id']:x for x in c.jsonlines(c.OUT/a.candidates)}
    rows=c.jsonlines(c.OUT/a.scores)
    iso_sel=iso_ref=end_sel=end_ref=0; j=[]
    for row in rows:
        pid=row['proposition_id']; scores=row['scores']; old=base[pid]; can=cans[pid]
        iso=baseline.core.select_evidence(can['api_C48'],scores,passages,prep[pid]['admission'])
        end=baseline.core.select_evidence(can['local_C48'],scores,passages,prep[pid]['admission'])
        iso_sel+=iso['selected_ids']==old['selected_ids']; iso_ref+=iso['reference']==old['reference']
        end_sel+=end['selected_ids']==old['selected_ids']; end_ref+=end['reference']==old['reference']
        sa=set(end['selected_ids']); sb=set(old['selected_ids']); j.append(len(sa&sb)/max(1,len(sa|sb)))
    print(json.dumps({'claims':len(rows),'isolated_reranker_selected_exact':iso_sel,'isolated_reranker_reference_exact':iso_ref,'end_to_end_selected_exact':end_sel,'end_to_end_reference_exact':end_ref,'end_selected_jaccard_mean':float(np.mean(j))},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
