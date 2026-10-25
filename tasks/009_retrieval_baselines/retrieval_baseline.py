"""Reusable 009 direct-claim retrieval and packing, with no API calls on import.

Supply real BGE-M3 dense vectors; rerank the returned candidate search_text with
the original claim, then pass real BGE scores to pack(). No source context enters.
"""
import math
import study009 as s

METHODS={'A48':'A','B48':'B','C48':'C'}


def retrieve(claim,passages,vectors,query_vector,method='C48'):
    if method not in METHODS:
        raise ValueError('Unknown frozen 009 baseline')
    if not isinstance(claim,str) or not claim.strip():
        raise ValueError('An unchanged nonempty claim is required')
    if passages:
        if len({p['subject_id'] for p in passages})!=1:
            raise ValueError('An index must belong to one known patient')
        ranks=s.core.HybridIndex(passages,vectors).retrieve(claim,query_vector,limit=80)
    else:
        ranks=dict(bm25=[],dense=[],hybrid=[])
    return dict(rankings=ranks,candidate_ids=s.candidates(ranks,METHODS[method],48))


def pack(candidate_ids,scores,passages,admission):
    if len(set(candidate_ids))!=len(candidate_ids) or len(candidate_ids)>48:
        raise ValueError('Expected distinct candidates with capacity 48')
    if set(candidate_ids)-set(scores):
        raise ValueError('Missing real rerank scores; do not fill with zero')
    if any(not math.isfinite(scores[k]) for k in candidate_ids):
        raise ValueError('Nonfinite rerank score')
    if len({passages[k]['subject_id'] for k in candidate_ids})>1:
        raise ValueError('Cross-patient evidence')
    return s.core.select_evidence(candidate_ids,scores,passages,admission,cap=8000,max_items=16,max_per_note=2)
