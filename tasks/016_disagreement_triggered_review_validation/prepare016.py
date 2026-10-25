"""Only the authorized next cohort; unchanged 009 raw-EHR/paragraph rules."""
from pathlib import Path
from collections import Counter,defaultdict
import argparse
import shutil
import common016 as c

def prepare(phase):
    ids=c.patient_ids(phase);expected=601
    out=c.OUT/phase/'preparation_002';c.require(not out.exists(),'Preparation exists')
    master=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv'
    formal=c.read(master.parent/'manifest.json')
    c.require(c.file_hash(master)==formal['output_sha256']['cohort_master.csv'],'002 cohort changed')
    rawfiles=[c.RAW/name for name in ('propositions/propositions.csv.gz','reference_ehr/admissions.csv.gz','reference_ehr/ehr_noteevents.csv.gz')]
    for p in rawfiles:c.require(c.file_hash(p)==formal['input_sha256'][p.relative_to(c.RAW).as_posix()],'Raw input changed')
    allrows=c.pilot.subset_csv(master,'subject_id',set(ids))
    cohort=sorted([r for r in allrows if r['proposition_type']=='claim' and r['invalid']=='False'],key=lambda r:int(r['human_csv_order']))
    c.require(len(cohort)==len({r['proposition_id'] for r in cohort})==expected,'Unexpected full cohort')
    props={r['proposition_id']:r for r in c.pilot.subset_csv(rawfiles[0],'subject_id',set(ids))}
    admissions={c.pilot.integer_id(a['SUBJECT_ID']):a for a in c.pilot.subset_csv(rawfiles[1],'SUBJECT_ID',set(ids))}
    notes=c.pilot.subset_csv(rawfiles[2],'SUBJECT_ID',set(ids));c.require(set(admissions)==set(ids),'Admissions mismatch')
    inputs=[]
    for i,r in enumerate(cohort,1):
        p=props[r['proposition_id']]
        c.require(c.pilot.integer_id(p['subject_id'])==r['subject_id'] and c.pilot.integer_id(p['hadm_id'])==r['hadm_id'],'Claim identity mismatch')
        inputs.append(dict(case_id=f'S{i:03d}' if phase=='stage1' else f'C{i:03d}',proposition_id=r['proposition_id'],subject_id=r['subject_id'],
            author_type=r['author_type'],text=p['text'],admission=admissions[r['subject_id']],claim_embedding_id=c.pilot.digest_text(p['text'])))
    corpus=[];excluded=[];coverage=defaultdict(set)
    for note in sorted(notes,key=lambda n:int(n['ROW_ID'])):
        sid=c.pilot.integer_id(note['SUBJECT_ID']);a=admissions[sid];date=note['CHARTDATE'][:10]
        reason='missing_chartdate' if not date else 'outside_admission_dates' if not a['ADMITTIME'][:10]<=date<=a['DISCHTIME'][:10] else 'discharge_summary' if note['CATEGORY'].strip().lower()=='discharge summary' else None
        if reason:
            excluded.append(dict(subject_id=sid,note_id=note['ROW_ID'],date=date,reason=reason));continue
        for lo,hi in c.baseline.core.paragraph_spans(note['TEXT']):
            p=dict(subject_id=sid,note_id=note['ROW_ID'],hadm_id=note['HADM_ID'],date=date,time=note['CHARTTIME'][11:] or 'Unknown',
                category=note['CATEGORY'],description=note['DESCRIPTION'],start=lo,end_exclusive=hi,text=note['TEXT'][lo:hi],note_sha256=c.pilot.digest_text(note['TEXT']))
            p['passage_id']=c.fingerprint(p);p['search_text']=f"Date: {p['date']}. {p['category']} {p['description']}. {p['text']}"
            p['embedding_id']=c.pilot.digest_text(p['search_text']);corpus.append(p);coverage[note['ROW_ID']].update(range(lo,hi))
        c.require(all(i in coverage[note['ROW_ID']] for i,ch in enumerate(note['TEXT']) if not ch.isspace()),'Raw nonwhite coverage lost')
    corpus.sort(key=lambda p:p['passage_id'])
    catalog={p['embedding_id']:p['search_text'] for p in corpus};catalog.update({p['claim_embedding_id']:p['text'] for p in inputs})
    c.require(all(0<len(t.encode())<8192 for t in catalog.values()),'Embedding text exceeds original bounds')
    jobs=c.embedding_jobs(catalog,'016_'+phase+'_embed')
    out.mkdir(parents=True)
    c.write_csv(out/'cohort.csv',cohort);c.write_csv(out/'invalid_claims.csv',[r for r in allrows if r['proposition_type']=='claim' and r['invalid']!='False'],list(cohort[0]))
    c.write_csv(out/'excluded_notes.csv',excluded,['subject_id','note_id','date','reason'])
    c.write_lines(out/'inputs.jsonl',inputs);c.write_lines(out/'corpus.jsonl',corpus);c.write_lines(out/'jobs.jsonl',jobs)
    c.write_json(out/'embedding_catalog.json',catalog)
    prompts=c.ROOT/'outputs/009_retrieval_baselines/confirmation_001/preparation/judge_prompts.json'
    (out/'judge_prompts.json').write_bytes(prompts.read_bytes())
    (out/'baseline_config.json').write_bytes((c.baseline.TASK/'baseline_config.json').read_bytes())
    summary=dict(phase=phase,patients=ids,claims=len(cohort),by_author=dict(Counter(r['author_type'] for r in cohort)),
        passages=len(corpus),indexed_notes=len(coverage),embedding_requests=len(jobs),embedding_texts=len(catalog),
        embedding_single_attempt_reservations=sum(c.bound(j) for j in jobs),paragraphs_nonwhite_coverage_checked=True,
        no_source_context_used=True,no_Judge_results_seen=True)
    c.write_json(out/'summary.json',summary)
    c.seal(out,[master,*rawfiles,prompts,c.baseline.TASK/'baseline_config.json',c.OUT/'protocol_002.md',c.ROOT/'outputs/003_error_analysis/patient_groups.json'],
        [Path(__file__),c.TASK/'common016.py',c.baseline.TASK/'study009.py',c.ROOT/'tasks/008_retrieval_planning/planning_core.py',c.ROOT/'tasks/008_retrieval_planning/prepare_experiment.py'])
    print(c.canonical(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('stage1',));prepare(p.parse_args().phase)
