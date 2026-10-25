"""Freeze all inputs and recipes for zero-API080."""
import csv
from collections import Counter,defaultdict
import common080 as c

def main():
    c.OUT.mkdir(exist_ok=False);sources={}
    def bind(p):sources[p.relative_to(c.ROOT).as_posix()]=c.sha(p)
    old=c.ROOT/'outputs/079_f4_priorg_adaptation'
    fitted=old/'fitted_models.json';cases=old/'calibration_predictions.jsonl';bind(fitted);bind(cases)
    ids=set(c.read(fitted)['common_ids'])
    train=[dict(id=x['id'],sid=x['sid'],GT=x['GT'],B=x['B']['parsed']['scores'],F4=x['F4']['parsed']['scores']) for x in c.lines(cases) if x['id'] in ids]
    assert len(train)==112 and len({x['sid'] for x in train})==14
    pg=c.ROOT/'outputs/051_thinking_mode_validation/freeze.json';bind(pg);p051=set(c.read(pg)['patient_pool'])
    mat=c.ROOT/'outputs/031_training_expansion_confirmation/judge_inputs_001/materials.jsonl';bind(mat)
    use={x['proposition_id'] for x in c.lines(mat) if str(x['subject_id']) in p051}
    cm=c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv';bind(cm)
    priorrows=[]
    for x in csv.DictReader(cm.open(encoding='utf-8-sig')):
        if x['proposition_id'] in use and x['invalid']=='False' and x['human_gt'] in c.LABELS:
            priorrows.append(dict(id=x['proposition_id'],sid=x['subject_id'],GT=x['human_gt']))
    counts=dict(Counter(x['GT'] for x in priorrows));assert counts=={'Supported':1108,'Not Supported':100,'Not Addressed':170},counts
    evalfile=old/'evaluation_blind.jsonl';bind(evalfile);ev=c.lines(evalfile)
    assert len(ev)==352 and not {x['sid'] for x in train}&{x['sid'] for x in ev}
    assert not {x['sid'] for x in priorrows}&{x['sid'] for x in ev}
    actualdemo=c.ROOT/'outputs/071_judge_icl_feasibility/freeze.json';bind(actualdemo)
    demo={x['sid'] for x in c.read(actualdemo)['examples']};assert not demo&({x['sid'] for x in train}|{x['sid'] for x in ev})
    c.jl(c.OUT/'calibration.jsonl',train);c.jl(c.OUT/'reference_prior_rows.jsonl',priorrows);c.jl(c.OUT/'evaluation_blind.jsonl',ev)
    for p in c.TASK.glob('*.py'):bind(p)
    bind(c.TASK/'README.md')
    sourceeval=old/'predictions.jsonl';bind(sourceeval)
    c.put(c.OUT/'freeze.json',dict(status='FROZEN_BEFORE_080_FITTING',created_utc=c.now(),new_API_calls=0,calibration_n=112,
        calibration_patients=14,evaluation_n=352,evaluation_patients=22,reference_prior_counts=counts,
        methods=['BASE','WNLL1','WNLL2','WMCC1','WMCC2'],selection='pooled patient-held-out reference-weighted MCC; then Macro-F1; then simpler recipe',
        source_sha256=sources,artifact_sha256={p.name:c.sha(p) for p in c.OUT.iterdir() if p.is_file()},gitignore_sha256=c.sha(c.ROOT/'.gitignore')))
    print(c.canon(dict(status='FROZEN',calibration=112,eval=352,reference=len(priorrows),API=0)))

if __name__=='__main__':main()
