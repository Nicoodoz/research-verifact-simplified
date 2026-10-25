"""Seal all source bindings and patient combinations before fitting."""
import subprocess
import common030 as c
def run():
    c.offline();c.require(not c.PREP.exists(),'Do not overwrite freeze');c.v.verify_frozen();env=c.environment();c.require('research-verifact-029' in env['executable'].lower(),'Dedicated environment required')
    config=c.read(c.TASK/'config.json');prior=c.v.PREP;rows=c.lines(prior/'full_rows.jsonl');features=c.lines(prior/'features.jsonl');original=c.read(prior/'config.json');schema=c.read(prior/'feature_schema.json')
    subjects=sorted({r['subject_id'] for r in rows});groups={r['subject_id']:r['group'] for r in features}
    c.require(len(rows)==1529 and len(features)==155 and len(subjects)==16 and len(groups)==15,'Wrong frozen scope');c.require(len({r['proposition_id'] for r in rows})==1529 and len({r['proposition_id'] for r in features})==155,'Duplicate IDs')
    c.require(all(schema['conditions'][m]==c.v.FEATURES[m] for m in config['methods']),'Feature order changed')
    sweeps,units=c.schedule(groups,config);unit_stats=[]
    for u in units:
        train=[r for r in features if r['subject_id'] in u['train_patients']];test=[r for r in features if r['subject_id']==u['held_patient']];fulltest=[r for r in rows if r['subject_id']==u['held_patient']]
        u.update(training_candidate_ids=[r['proposition_id'] for r in train],test_candidate_ids=[r['proposition_id'] for r in test],test_claim_ids=[r['proposition_id'] for r in fulltest],train_candidates=len(train),train_R=sum(r['human_gt']=='Supported' for r in train),train_risk=sum(r['human_gt']!='Supported' for r in train),test_patients=1,test_candidates=len(test),test_claims=len(fulltest))
        unit_stats.append({k:v for k,v in u.items() if not k.endswith('_ids')})
    unique_models={(m,tuple(u['train_patients'])) for u in units for m in config['methods']};c.PREP.mkdir(parents=True)
    # Byte-identical original scientific inputs and original frozen learning settings.
    for name in ('full_rows.jsonl','features.jsonl'):(c.PREP/name).write_bytes((prior/name).read_bytes())
    c.put(c.PREP/'config.json',config);c.put(c.PREP/'learning_config.json',original);c.put(c.PREP/'feature_schema.json',dict(conditions={m:schema['conditions'][m] for m in config['methods']},original_schema_sha256=c.sha(prior/'feature_schema.json'),fields=[r for r in schema['fields'] if r['name'] in c.v.FEATURES['D']]))
    c.put(c.PREP/'sweeps.json',sweeps);c.jsonl(c.PREP/'units.jsonl',units);c.csvwrite(c.PREP/'unit_summary.csv',unit_stats);c.put(c.PREP/'environment.json',env);c.write_text(c.PREP/'protocol.md',(c.TASK/'protocol.md').read_text(encoding='utf-8'))
    c.put(c.PREP/'scope.json',dict(full_claims=len(rows),candidates=len(features),patients=subjects,candidate_patients=groups,no_candidate_patients=sorted(set(subjects)-set(groups)),scheduled_sweeps=len(sweeps),unique_sweeps=len({s['canonical_sweep'] for s in sweeps}),scheduled_units=len(units),unique_model_fits=len(unique_models),API_calls=0,selection_reads_GT=False))
    sources=[prior/'manifest.json',prior/'full_rows.jsonl',prior/'features.jsonl',prior/'config.json',prior/'feature_schema.json',prior/'environment.json',c.ROOT/'reviews/029_semantic_information_gate.md']
    for m in config['methods']:sources.append(c.v.OUT/'run_001/patient_OOF'/f'{m}-Logistic'/'predictions.json')
    code=list(c.TASK.glob('*.py'))+list(c.TASK.glob('*.ps1'))+[c.TASK/'config.json',c.TASK/'protocol.md']
    # Bind the old deterministic learning/metrics chain, not old mutable navigation.
    code.extend(c.ROOT/p for p in c.read(prior/'manifest.json')['code'])
    c.put(c.PREP/'manifest.json',dict(created_utc=c.now(),git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sources},files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in c.PREP.iterdir() if p.is_file()},code={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in set(code)},formal_fits_before_freeze=0));print(c.read(c.PREP/'scope.json'))
if __name__=='__main__':run()
