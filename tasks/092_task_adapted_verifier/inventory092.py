"""Read-only inventory; no clinical text is printed or publicly exported."""
import csv,json,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def lines(p):
    with p.open(encoding='utf-8-sig') as f:
        for line in f:
            if line.strip():yield json.loads(line)
master=list(csv.DictReader((R/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig')))
print('master',len(master),collections.Counter((r['proposition_type'],r['invalid']) for r in master))
sources=['032_evidence_relation_correction/preparation_001/inputs_blind.jsonl','036_final_validation/judge_inputs_001/materials.jsonl','018_verifact_gap_attribution/preparation_001/materials.jsonl','012_comparative_error_diagnosis/alignment_002/aligned_materials.jsonl']
ids=set()
for name in sources:
    p=R/'outputs'/name
    rr=list(lines(p));ids.update(r.get('proposition_id',r.get('id')) for r in rr)
    print(name,'n',len(rr),'keys',list(rr[0]),'patients',len({r.get('subject_id',r.get('sid')) for r in rr}))
print('covered master',collections.Counter((r['proposition_type'],r['invalid']) for r in master if r['proposition_id'] in ids))
print('missing valid atomic',collections.Counter(r['subject_id'] for r in master if r['proposition_id'] not in ids and r['proposition_type']=='claim' and r['invalid']=='False'))
for name in ['009_retrieval_baselines/development_001/judge_preparation/inputs.jsonl','009_retrieval_baselines/confirmation_001/judge_preparation/inputs.jsonl','008_retrieval_planning/preparation_001/inputs.jsonl','008_retrieval_planning/preparation_001/corpus.jsonl']:
    rr=list(lines(R/'outputs'/name));print(name,len(rr),list(rr[0]),len({r.get('subject_id') for r in rr}))
    if 'retrieval' in rr[0]:print('retrievalkeys',list(rr[0]['retrieval']))
