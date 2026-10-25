"""Program facts about intervention coverage; none are medical recall metrics."""
from collections import Counter,defaultdict
from pathlib import Path
import study013 as s
from prepare013 import source_data,ANCHORS

def run(out=None):
    out=out or s.OUT/'screen_input_diagnostics_001'
    items,pp,notes,prompts=source_data();old={x['proposition_id']:x for x in items}
    records=s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl')
    rows=[];anchors=[]
    for x in records:
        origin=old[x['proposition_id']];base=x['retrieval']['baseline'];pool=set(origin['retrieval']['C48']['candidate_ids'])
        for arm,r in x['retrieval'].items():
            selected=set(r['selected_ids']);per_note=Counter(pp[k]['note_id'] for k in selected)
            assert r['body_characters']<=8000 and len(selected)<=16
            if arm=='selector':assert selected<=pool
            if arm in ('baseline','contract','text_guard','refresh48'):assert selected<=pool
            assert all(pp[k]['subject_id']==x['subject_id'] for k in selected)
            changes=r.get('repairs',[]);base_repair_ids=set(base['selected_ids'])&{z['passage_id'] for z in changes}
            rows.append(dict(case_id=x['case_id'],proposition_id=x['proposition_id'],subject_id=x['subject_id'],author_type=x['author_type'],arm=arm,
                same_reference_as_baseline=r['reference']==base['reference'],selected=len(selected),notes=len(per_note),
                body_characters=r['body_characters'],more_than_two_from_note=sum(n>2 for n in per_note.values()),
                lost_from_baseline=len(set(base['selected_ids'])-selected),added_to_baseline=len(selected-set(base['selected_ids'])),
                candidate_count=len(r.get('real_rerank_scores',pool)),new_candidate_selected=len(selected-pool),
                baseline_selected_prefix_repairs=len(base_repair_ids),retained_prefix_repairs=len(base_repair_ids&selected),
                dropped_repair_ids=sorted(base_repair_ids-selected),
                final_added_prefix_characters=sum(z['added_characters'] for z in changes if z['passage_id'] in selected),
                generic_short_marker_count=sum(len(pp[k]['text'].strip())<40 for k in selected),
                skip_counts=dict(Counter(z['reason'] for z in r.get('selection_skips',[]))),
                selector_status=r.get('selector_status')))
            if x['case_id'] in ANCHORS:
                for key in ANCHORS[x['case_id']]:
                    p=pp[key]
                    raw=notes[p['note_id']]['TEXT'];assert raw[p['start']:p['end_exclusive']]==p['text']
                    scores=r.get('real_rerank_scores',origin['scores'])
                    eligible=set(scores) if arm=='wide_candidates' else pool
                    rank=sorted(eligible,key=lambda k:(-scores[k],k)).index(key)+1 if key in eligible else None
                    anchors.append(dict(case_id=x['case_id'],arm=arm,passage_id=key,note_id=p['note_id'],start=p['start'],end_exclusive=p['end_exclusive'],
                        raw_sha256=s.pilot.digest_text(raw),text=p['text'],eligible=key in eligible,
                        selected=key in selected,rerank_rank=rank,rank_note='selector still uses old BGE ranking as input; selection priority is separate',
                        first_skip=next((z['reason'] for z in r.get('selection_skips',[]) if z['passage_id']==key),None)))
    summary={}
    for arm in sorted({r['arm'] for r in rows}):
        own=[r for r in rows if r['arm']==arm]
        summary[arm]=dict(claims=len(own),changed_references=sum(not r['same_reference_as_baseline'] for r in own),
            selected_occurrences=sum(r['selected'] for r in own),mean_body_characters=sum(r['body_characters'] for r in own)/len(own),
            lost_original_occurrences=sum(r['lost_from_baseline'] for r in own),new_selected_occurrences=sum(r['added_to_baseline'] for r in own),
            new_candidate_occurrences_in_final=sum(r['new_candidate_selected'] for r in own),
            note_quota_exceptions=sum(r['more_than_two_from_note'] for r in own),
            baseline_prefix_repair_opportunities=sum(r['baseline_selected_prefix_repairs'] for r in own),
            retained_prefix_repairs=sum(r['retained_prefix_repairs'] for r in own),
            selector_fallbacks=sum(r['selector_status']=='fallback_invalid_or_missing' for r in own))
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'per_claim.jsonl',rows);s.pilot.write_json(out/'anchors.json',anchors)
    s.pilot.write_json(out/'summary.json',dict(methods=summary,not_medical_gold_or_error_prevalence=True))
    s.freeze(out,[s.OUT/'screen_inputs_001/manifest.json'],[Path(__file__)])
    print(s.pilot.canonical(summary))

if __name__=='__main__':run()
