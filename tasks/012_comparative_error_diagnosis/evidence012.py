"""Trace existing spans through C48; scan literal polarity-boundary candidates."""
from pathlib import Path
from collections import Counter
import re
import argparse
import study012 as s

def trace(item,corpus,note,lo,hi):
    assert note['SUBJECT_ID']==item['subject_id'] and 0<=lo<hi<=len(note['TEXT'])
    pool=item['retrieval']['C48']['candidate_ids'];selected=item['retrieval']['C48']['selected_ids']
    rr=sorted(pool,key=lambda k:(-item['scores'][k],k));skips={x['passage_id']:x['reason'] for x in item['retrieval']['C48']['selection_skips']}
    rankings={a:{k:i+1 for i,(k,_) in enumerate(item['rankings'][a])} for a in ('dense','bm25')}
    hybrid={k:i+1 for i,k in enumerate(item['rankings']['hybrid'])}
    rows=[]
    for p in corpus:
        if p['note_id']!=note['ROW_ID'] or p['end_exclusive']<=lo or p['start']>=hi:continue
        key=p['passage_id']
        rows.append(dict(passage_id=key,start=p['start'],end_exclusive=p['end_exclusive'],overlap=[max(lo,p['start']),min(hi,p['end_exclusive'])],
            whole_anchor_in_one_passage=p['start']<=lo and hi<=p['end_exclusive'],dense_rank=rankings['dense'].get(key),bm25_rank=rankings['bm25'].get(key),
            fusion_rank=hybrid.get(key),C_candidate_rank=pool.index(key)+1 if key in pool else None,
            shared_reranker_scored=key in item['scores'],C_rerank_rank=rr.index(key)+1 if key in rr else None,
            score=item['scores'].get(key),selected_ordinal=selected.index(key)+1 if key in selected else None,first_skip=skips.get(key)))
    return dict(note_id=note['ROW_ID'],subject_id=note['SUBJECT_ID'],raw_sha256=s.pilot.digest_text(note['TEXT']),start=lo,end_exclusive=hi,
        quote=note['TEXT'][lo:hi],chartdate=note['CHARTDATE'],charttime=note['CHARTTIME'],category=note['CATEGORY'],description=note['DESCRIPTION'],
        indexed=bool(rows),passages=rows,original_upstream='unavailable; no original rankings inferred')

def run(out):
    s.check(s.OUT/'materials_001')
    corpus=s.pilot.jsonl(s.OUT/'materials_001/corpus.jsonl');pp={p['passage_id']:p for p in corpus}
    nn={n['ROW_ID']:n for n in s.pilot.jsonl(s.OUT/'materials_001/ehr_notes.jsonl')}
    allitems=s.pilot.jsonl(s.NINE/'judge_preparation/inputs.jsonl')
    risks=[];counts=[]
    for item in allitems:
        ret=item['retrieval']['C48']
        for key in ret['selected_ids']:
            p=pp[key];text=nn[p['note_id']]['TEXT'];prefix=text[max(0,p['start']-40):p['start']]
            m=re.search(r'\b(No|not|without|denies)\s*$',prefix,re.I)
            if m:
                lo=max(0,p['start']-40)+m.start();hi=min(len(text),p['start']+80)
                risks.append(dict(case_id=item['case_id'],proposition_id=item['proposition_id'],
                    category='machine_polarity_boundary_candidate_not_clinical_error',trace=trace(item,corpus,nn[p['note_id']],lo,hi)))
        counts.append(dict(case_id=item['case_id'],proposition_id=item['proposition_id'],C_candidates=len(ret['candidate_ids']),C_selected=len(ret['selected_ids']),
            first_skip_counts=dict(Counter(x['reason'] for x in ret['selection_skips'])),C_all_scores_present=set(ret['candidate_ids'])<=set(item['scores'])))
        reconstructed=s.source.previous.core.select_evidence(ret['candidate_ids'],item['scores'],pp,item['admission'])
        assert reconstructed=={k:ret[k] for k in reconstructed}
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'C_pipeline_checks.jsonl',counts)
    s.pilot.write_json(out/'boundary_candidates.json',risks)
    s.pilot.write_json(out/'summary.json',dict(C_references_reconstructed=len(counts),polarity_boundary_occurrences=len(risks),
        polarity_boundary_claims=len({r['case_id'] for r in risks}),not_medical_error_prevalence=True,original_upstream_unavailable=True))
    s.seal(out,[s.OUT/'materials_001/manifest.json',s.NINE/'judge_preparation/inputs.jsonl'],[Path(__file__)])
    print(s.pilot.canonical(s.read_json(out/'summary.json')))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=s.OUT/'pipeline_001')
    run(ap.parse_args().output)
