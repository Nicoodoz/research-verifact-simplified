"""Local inference adapter; consumes only pre-Judge retrieval information."""
from pathlib import Path
import json
import common044 as c
from selector044 import propose
from stages044 import choose

def recover_evidence(claim,base_reference,base_ids,candidate_ids,rerank_scores,passages,model):
    packs=propose(claim,base_reference,base_ids,candidate_ids,rerank_scores,passages)
    selected,utilities=choose(model,{'packs':packs})
    ref=base_reference if selected=='base' else packs[selected]['reference']
    ids=[] if selected=='base' else packs[selected]['ids']
    return dict(reference=ref,appended_passage_ids=ids,selected_pack=selected,estimated_utilities=utilities,
      added_characters=len(ref)-len(base_reference),additional_API_calls=0)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('input_json'); parser.add_argument('output_json')
    parser.add_argument('--model',default=str(c.OUT/'model/final.json')); args=parser.parse_args()
    payload=c.read(args.input_json)
    required={'claim','base_reference','base_ids','candidate_ids','rerank_scores','passages'}
    if set(payload)!=required: raise ValueError('Only the six pre-Judge retrieval fields are accepted')
    result=recover_evidence(**payload,model=c.read(args.model))
    c.put(args.output_json,result)
