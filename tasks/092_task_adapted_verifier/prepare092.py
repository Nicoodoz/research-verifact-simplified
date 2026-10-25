"""All valid atomic claims; reuse exact C48; prepare missing local C48 without labels."""
import sys,collections,gzip
import common092 as c
sys.path.insert(0,str(c.ROOT/'tasks/009_retrieval_baselines'))
import study009 as old
def main():
    c.OUT.mkdir(exist_ok=True);c.PRIVATE.mkdir(exist_ok=True)
    gt={r['proposition_id']:r for r in c.csvrows(c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv') if r['proposition_type']=='claim' and r['invalid']=='False'}
    original={r['proposition_id']:r['verdict'] for author in ['human','llm'] for r in c.csvrows(c.ROOT/f'outputs/002_reproduce_paper_results/run_003/baseline_predictions/R1-70B_{author}_claim_valid_only.csv')}
    sources=['032_evidence_relation_correction/preparation_001/inputs_blind.jsonl','036_final_validation/judge_inputs_001/materials.jsonl'];cached={}
    for src in sources:
        for r in c.lines(c.ROOT/'outputs'/src):
            pid=r['proposition_id'];assert pid in gt and str(r['subject_id'])==gt[pid]['subject_id']
            cached[pid]={k:r[k] for k in ['proposition_id','text','reference']};cached[pid]['source']=src
    missing=set(gt)-set(cached);subjects={gt[p]['subject_id'] for p in missing}
    def rawcsv(name):
        with gzip.open(old.RAW/name,'rt',encoding='utf-8',newline='') as f:return list(__import__('csv').DictReader(f))
    props={r['proposition_id']:r for r in rawcsv('propositions/propositions.csv.gz') if r['proposition_id'] in missing}
    admissions={str(int(r['SUBJECT_ID'])):r for r in rawcsv('reference_ehr/admissions.csv.gz') if str(int(r['SUBJECT_ID'])) in subjects}
    corpus=[]
    for note in rawcsv('reference_ehr/ehr_noteevents.csv.gz'):
        sid=str(int(note['SUBJECT_ID']))
        if sid not in subjects:continue
        ad=admissions[sid];date=note['CHARTDATE'][:10]
        if not date or not ad['ADMITTIME'][:10]<=date<=ad['DISCHTIME'][:10] or note['CATEGORY'].strip().lower()=='discharge summary':continue
        for lo,hi in old.core.paragraph_spans(note['TEXT']):
            p=dict(subject_id=sid,note_id=note['ROW_ID'],hadm_id=note['HADM_ID'],date=date,time=note['CHARTTIME'][11:] or 'Unknown',category=note['CATEGORY'],description=note['DESCRIPTION'],start=lo,end_exclusive=hi,text=note['TEXT'][lo:hi],note_sha256=c.digest(note['TEXT']))
            p['passage_id']=old.pilot.fingerprint(p);p['search_text']=f"Date: {p['date']}. {p['category']} {p['description']}. {p['text']}";p['embedding_id']=c.digest(p['search_text']);corpus.append(p)
    inputs=[dict(proposition_id=pid,subject_id=gt[pid]['subject_id'],text=props[pid]['text'],admission=admissions[gt[pid]['subject_id']]) for pid in sorted(missing)]
    c.jsonl(c.PRIVATE/'cached_c48.jsonl',list(cached.values()));c.jsonl(c.PRIVATE/'missing_inputs.jsonl',inputs);c.jsonl(c.PRIVATE/'missing_corpus.jsonl',sorted(corpus,key=lambda r:r['passage_id']))
    # Public metadata contains no claim/reference or private receipt.
    groups=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups'];role={str(s):k for k,v in groups.items() for s in v}
    c.jsonl(c.OUT/'cohort.jsonl',[dict(id=p,sid=r['subject_id'],author=r['author_type'],GT=r['human_gt'],original=original[p],historical_role=role[r['subject_id']]) for p,r in sorted(gt.items())])
    c.put(c.OUT/'inventory.json',dict(n=len(gt),patients=len({r['subject_id'] for r in gt.values()}),cached=len(cached),missing=len(missing),missing_patients=len(subjects),missing_corpus=len(corpus),new_API_calls=0,source_hashes={s:c.sha(c.ROOT/'outputs'/s) for s in sources}))
    print(c.read(c.OUT/'inventory.json'),flush=True)
if __name__=='__main__':main()
