import csv,json,collections
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def jl(p): return [json.loads(s) for s in (R/p).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
f=json.loads((R/'outputs/072_adaptive_judge_examples/freeze.json').read_text())
a={x['proposition_id']:x for x in csv.DictReader((R/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv').open(encoding='utf-8-sig'))}
m=jl('outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl')
print('annotation fields',list(next(iter(a.values()))))
for stage,ss in [('train',f['teaching_patients']),('pilot',f['pilot_patients']),('confirm',f['confirmation_patients'])]:
 rows=[x for x in m if x['subject_id'] in ss and x['author_type']=='llm' and a[x['proposition_id']]['human_gt'] in ('Supported','Not Supported','Not Addressed')]
 print(stage,len(rows),collections.Counter(a[x['proposition_id']]['human_gt'] for x in rows))
 if stage=='train':
  clean=[x for x in rows if a[x['proposition_id']]['initial_agreement']=='3' and a[x['proposition_id']]['second_round_anomaly']=='False' and a[x['proposition_id']]['time_metadata_conflict']=='False']
  print('clean',collections.Counter(a[x['proposition_id']]['human_gt'] for x in clean))
  for x in clean:
   if a[x['proposition_id']]['human_gt']=='Not Supported': print(x['proposition_id'],x['subject_id'],x['text'])
ids=set(json.loads((R/'outputs/031_training_expansion_confirmation/materials_001/embedding_ids.json').read_text()))
inputs=jl('outputs/031_training_expansion_confirmation/materials_001/inputs.jsonl')
print('cached',len(inputs),sum(x['claim_embedding_id'] in ids for x in inputs))
print('prediction fields',next(csv.DictReader((R/'outputs/031_training_expansion_confirmation/analysis_001/predictions.csv').open(encoding='utf-8-sig'))))
