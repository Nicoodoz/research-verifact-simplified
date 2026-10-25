"""Offline full-cohort packing and fixed pilot selection; no inference calls."""
from pathlib import Path
from collections import Counter
import argparse
import statistics
import study011 as s
import packaging011 as p


def prepare(out):
    assert not out.exists()
    cohort=s.pilot.read_csv(s.PRIOR/'preparation/cohort.csv')[1]
    items=s.pilot.jsonl(s.PRIOR/'judge_preparation/inputs.jsonl')
    assert len(cohort)==len(items)==650
    subjects={x['subject_id'] for x in items}
    assert subjects==set(s.previous.patient_order()[18:24])
    corpus=s.pilot.jsonl(s.PRIOR/'preparation/corpus.jsonl')
    note_ids={x['note_id'] for x in corpus}
    notes={x['ROW_ID']:x for x in s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',subjects) if x['ROW_ID'] in note_ids}
    assert set(notes)==note_ids
    geometry={nid:p.geometry(n['TEXT']) for nid,n in notes.items()}
    views={x['passage_id']:p.make_views(x,notes[x['note_id']],geometry[x['note_id']]) for x in corpus}
    records=[];features=[]
    for item in items:
        pool=item['retrieval']['C48']['candidate_ids'];scores=item['scores']
        assert set(pool)<=set(scores) and all(views[k]['A']['subject_id']==item['subject_id'] for k in pool)
        arms={a:p.pack(pool,scores,views,item['admission'],a) for a in s.METHODS}
        assert arms['A']['reference']==item['retrieval']['C48']['reference']
        row={k:item[k] for k in ('case_id','proposition_id','subject_id','author_type','text','admission')}
        records.append(dict(row,candidate_ids=pool,scores={k:scores[k] for k in pool},retrieval=arms))
        for arm in s.METHODS:
            ids=arms[arm]['selected_ids'];old=arms['A']['selected_ids'];base=arms['B']['selected_ids']
            selected=[views[k][arm] for k in ids]
            features.append(dict(case_id=item['case_id'],author_type=item['author_type'],subject_id=item['subject_id'],arm=arm,
                selected=len(ids),body_characters=arms[arm]['body_characters'],notes=len({x['note_id'] for x in selected}),
                lost_A=len(set(old)-set(ids)),added_vs_A=len(set(ids)-set(old)),lost_B=len(set(base)-set(ids)),added_vs_B=len(set(ids)-set(base)),
                boundary_added=sum(x.get('repair',{}).get('added',0) for x in selected),
                unrepaired_edges=sum(len(x.get('repair',{}).get('unresolved',[])) for x in selected),
                context_fields=sum(len(x.get('source_context',[])) for x in selected),
                context_characters=sum(len(h['text']) for x in selected for h in x.get('source_context',[])),
                identical_to_B=arms[arm]['reference']==arms['B']['reference']))
    gt={r['proposition_id']:r['human_gt'] for r in cohort}
    bycase={r['case_id']:r for r in records}
    chosen={cid:['prespecified prior positive/negative/uncertain probe'] for cid in ('N071','N180','N642','N561','N563','N394','N420','N430','N585','N119')}
    for sid in sorted(subjects):
        for author in ('llm','human'):
            if any(bycase[cid]['subject_id']==sid and bycase[cid]['author_type']==author for cid in chosen):continue
            available=[r for r in records if r['subject_id']==sid and r['author_type']==author]
            cid=min(available,key=lambda r:s.pilot.digest_text('011/pilot/patient/v1:'+r['proposition_id']))['case_id']
            chosen[cid]=['patient/author coverage by frozen hash']
    for author in ('llm','human'):
        while sum(bycase[c]['author_type']==author for c in chosen)<12:
            counts=Counter(gt[bycase[c]['proposition_id']] for c in chosen if bycase[c]['author_type']==author)
            label=min(('Not Supported','Not Addressed','Supported'),key=lambda l:counts[l])
            available=[r for r in records if r['author_type']==author and gt[r['proposition_id']]==label and r['case_id'] not in chosen]
            if not available:available=[r for r in records if r['author_type']==author and r['case_id'] not in chosen]
            cid=min(available,key=lambda r:s.pilot.digest_text('011/pilot/class/v1:'+r['proposition_id']))['case_id']
            chosen[cid]=['fill original-label coverage by frozen hash']
    assert len(chosen)==24
    summary=dict(claims=650,notes=len(notes),original_passages=len(views),candidate_order_and_scores_unchanged=True,A_byte_identical_to_009=True,
        scope=dict(patients=sorted(subjects),labels={a:dict(Counter(gt[r['proposition_id']] for r in records if r['author_type']==a)) for a in ('llm','human')}),
        by_arm={a:{k:sum(r[k] for r in features if r['arm']==a) for k in ('selected','lost_A','added_vs_A','lost_B','added_vs_B','boundary_added','unrepaired_edges','context_fields','context_characters')} for a in s.METHODS},
        C_B_changed=sum(not r['identical_to_B'] for r in features if r['arm']=='C'),
        pilot_cases=sorted(chosen),pilot_labels={a:dict(Counter(gt[bycase[c]['proposition_id']] for c in chosen if bycase[c]['author_type']==a)) for a in ('llm','human')})
    out.mkdir(parents=True)
    (out/'cohort.csv').write_bytes((s.PRIOR/'preparation/cohort.csv').read_bytes())
    s.pilot.write_jsonl(out/'inputs.jsonl',records)
    s.pilot.write_jsonl(out/'views.jsonl',[dict(passage_id=k,views=v) for k,v in views.items()])
    s.pilot.write_json(out/'pilot_selection.json',chosen)
    s.pilot.write_csv(out/'features.csv',features)
    s.pilot.write_json(out/'summary.json',summary)
    s.pilot.write_json(out/'judge_prompts.json',s.read_json(s.PRIOR/'preparation/judge_prompts.json'))
    s.seal(out,[s.PRIOR/'judge_preparation/inputs.jsonl',s.PRIOR/'preparation/corpus.jsonl',s.PRIOR/'preparation/cohort.csv',s.RAW/'reference_ehr/ehr_noteevents.csv.gz'],[Path(__file__),s.TASK/'packaging011.py',s.TASK/'study011.py'])
    print(s.pilot.canonical(summary))


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    prepare(ap.parse_args().output.resolve())
