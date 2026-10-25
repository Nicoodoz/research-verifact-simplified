"""Whole-screen surface execution metrics and registered/local raw trace probes."""
from pathlib import Path
from collections import Counter,defaultdict
import json
import study013 as s
import mechanisms013 as m
from prepare013 import source_data,ANCHORS

def run(out=None):
    out=out or s.OUT/'mechanism_analysis_001'
    items,pp,notes,prompts=source_data();old={x['case_id']:x for x in items}
    inputs={x['case_id']:x for x in s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl')}
    rows={r['case_id']:r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/transitions.jsonl')}
    outputs={r['request_id']:r for r in s.pilot.jsonl(s.OUT/'screen_analysis_001/normalized_responses.jsonl')}
    assignments=s.pilot.read_csv(s.OUT/'screen_judge_preparation_001/assignments.csv')[1]
    copyrows=[];usage=defaultdict(list);mapped={}
    for a in assignments:
        if a['round']!='0':continue
        cid=a['case_id'];arm=a['arm'];v=outputs[a['request_id']];mapped[(cid,arm)]=v
        obj=s.pilot.strict_json(v['output_text'])
        checks=obj.get('checks',[])
        summaries=[c.get('assessment','') for c in checks if str(c.get('aspect','')).strip().lower().replace(' ','_')=='claim_summary']
        rawclaim=inputs[cid]['text']
        copyrows.append(dict(case_id=cid,arm=arm,contract_applicable=m.literal_contract(rawclaim) is not None,
            verbatim_claim_in_summary=any(rawclaim in t for t in summaries),
            verbatim_claim_in_any_assessment=any(rawclaim in c.get('assessment','') for c in checks),
            adherence_errors=v['adherence_errors']))
        usage[arm].append(dict(input_tokens=v['usage']['input_tokens'],output_tokens=v['usage']['output_tokens'],words=v['explanation_words'],
            adherence_flag=bool(v['adherence_errors'])))
    contract_summary={}
    for arm in ('baseline','contract'):
        own=[r for r in copyrows if r['arm']==arm and r['contract_applicable']]
        contract_summary[arm]=dict(applicable=len(own),verbatim_summary=sum(r['verbatim_claim_in_summary'] for r in own),
            verbatim_any_assessment=sum(r['verbatim_claim_in_any_assessment'] for r in own),not_semantic_fidelity_rate=True)
    probe_ids={cid:list(ids) for cid,ids in ANCHORS.items()}
    for cid,nid,start in [('N585','474161',639),('N425','470890',0),('N147','400203',0),('N182','626473',3824),('N530','473395',1911),('N501','473836',0)]:
        p=next(p for p in pp.values() if p['note_id']==nid and p['start']==start)
        probe_ids.setdefault(cid,[]).append(p['passage_id'])
    traces=[]
    for cid,ids in probe_ids.items():
        if cid not in inputs:continue
        x=inputs[cid];b=old[cid];basepool=set(b['retrieval']['C48']['candidate_ids'])
        for key in ids:
            p=pp[key];raw=notes[p['note_id']]['TEXT'];assert raw[p['start']:p['end_exclusive']]==p['text']
            arms={}
            for arm,r in x['retrieval'].items():
                score=x['retrieval']['wide_candidates']['real_rerank_scores'] if arm in ('wide_candidates','refresh48') else b['scores']
                pool=set(score) if arm=='wide_candidates' else basepool
                rank=sorted(pool,key=lambda k:(-score[k],k)).index(key)+1 if key in pool else None
                arms[arm]=dict(candidate_eligible=key in pool,real_rerank_score=score.get(key),rerank_rank=rank,
                    selected=key in r['selected_ids'],first_skip=next((z['reason'] for z in r.get('selection_skips',[]) if z['passage_id']==key),None),
                    verdict=rows[cid][arm])
            traces.append(dict(case_id=cid,proposition_id=x['proposition_id'],claim=x['text'],human_gt=rows[cid]['human_gt'],
                passage_id=key,note_id=p['note_id'],subject_id=p['subject_id'],start=p['start'],end_exclusive=p['end_exclusive'],
                raw_note_sha256=s.pilot.digest_text(raw),raw_text=p['text'],arms=arms,not_medical_gold=True))
    prefix=[]
    for cid in ('N580','N585'):
        r=inputs[cid]['retrieval']['text_guard']
        for z in r['repairs']:
            if z['passage_id'] not in r['selected_ids']:continue
            raw=notes[z['note_id']]['TEXT'];lo=max(0,z['new_start']-120);hi=min(len(raw),z['old_start']+100)
            prefix.append(dict(case_id=cid,**z,context_start=lo,context_end=hi,context=raw[lo:hi],
                role='raw scope backcheck; added prefix may begin in another clinical field, not guaranteed complete condition binding'))
    summaries={arm:{key:sum(r[key] for r in v)/len(v) for key in ('input_tokens','output_tokens','words','adherence_flag')} for arm,v in usage.items()}
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'contract_execution.jsonl',copyrows)
    s.pilot.write_json(out/'contract_summary.json',contract_summary)
    s.pilot.write_json(out/'effective_usage_per_condition.json',dict(methods=summaries,shared_requests_not_double_billed=True))
    s.pilot.write_json(out/'raw_traces.json',traces);s.pilot.write_json(out/'prefix_scope_backchecks.json',prefix)
    s.freeze(out,[s.OUT/'screen_inputs_001/manifest.json',s.OUT/'screen_analysis_001/normalized_responses.jsonl'],[Path(__file__)])
    print(s.pilot.canonical(contract_summary));print(s.pilot.canonical(summaries))

if __name__=='__main__':run()
