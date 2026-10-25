"""002 evaluation and predeclared multi-criterion screening gates, no label repair."""
from collections import Counter
import math,argparse
import study013 as s
from io013 import stage,normalize
from score009 import evaluate_scope,movement

def gate_statistics(rows,before,after,minimum=7):
    moves=[movement(r.get(before),r.get(after),r['human_gt']) for r in rows]
    total=Counter(moves);net=total['improved']-total['worsened']
    patients={sid:sum((r.get(after)==r['human_gt'])-(r.get(before)==r['human_gt']) for r in rows if r['subject_id']==sid) for sid in sorted({r['subject_id'] for r in rows})}
    authors={};cost_ok=True
    for a in ('llm','human'):
        own=[r for r in rows if r['author_type']==a]
        classes={g:{method:sum(r.get(method)==g for r in own if r['human_gt']==g) for method in (before,after)} for g in ('Supported','Not Supported','Not Addressed')}
        errors={method:sum(r['human_gt']!='Supported' and r.get(method)=='Supported' for r in own) for method in (before,after)}
        authors[a]=dict(net=sum(r.get(after)==r['human_gt'] for r in own)-sum(r.get(before)==r['human_gt'] for r in own),classes=classes,false_supported=errors)
        cost_ok &= errors[after]-errors[before]<=1 and all(classes[g][after]-classes[g][before]>=-1 for g in ('Not Supported','Not Addressed'))
    positive=sum(max(v,0) for v in patients.values())
    checks=dict(complete='missing' not in total,net_gain=net>=minimum,gain_loss_ratio=total['improved']>=1.5*total['worsened'],
        author_directions=all(v['net']>=0 for v in authors.values()),positive_patients=sum(v>0 for v in patients.values())>=3,
        leave_one_patient_positive=all(net-v>0 for v in patients.values()),
        not_single_patient_dominated=positive>0 and max(patients.values())<=.6*positive,minority_costs=bool(cost_ok))
    return dict(before=before,after=after,transitions=dict(total),net=net,patients=patients,authors=authors,
        checks=checks,statistical_gate=all(checks.values()),mechanism_review_still_required=True)

def run(output=None):
    phase='screen_judge';prep=s.OUT/f'{phase}_preparation_001'
    assert not (s.OUT/'live'/phase/'runner.lock').exists()
    s.check(prep);values,attempts=stage(phase)
    cohort=s.pilot.read_csv(s.OUT/'preparation_001/screen_cohort.csv')[1]
    assignments=s.pilot.read_csv(prep/'assignments.csv')[1]
    pids={a['request_id']:a['proposition_id'] for a in assignments}
    normalized={rid:normalize(v['job'],v['receipt'],pids[rid]) for rid,v in values.items()}
    methods=['baseline',*s.read_json(s.OUT/'unit_analysis_001/gate.json')['eligible_methods']]
    if 'wide_candidates' in methods:methods+=['refresh48']
    predictions={a:[] for a in methods};lookup={a:{} for a in methods};repeats=[]
    for a in assignments:
        n=normalized[a['request_id']]
        if a['round']=='0' and n['status']=='success':
            predictions[a['arm']].append(dict(proposition_id=a['proposition_id'],verdict=n['verdict']))
            lookup[a['arm']][a['proposition_id']]=n['verdict']
    for a in assignments:
        if a['round']!='0':
            n=normalized[a['request_id']];first=lookup['baseline'].get(a['proposition_id'])
            repeats.append(dict(a,canonical_verdict=first,repeat_verdict=n.get('verdict'),repeat_status=n['status'],changed=first!=n.get('verdict')))
    inputrows=s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl');inputs={r['proposition_id']:r for r in inputrows}
    rows=[dict(r,case_id=inputs[r['proposition_id']]['case_id'],**{a:lookup[a].get(r['proposition_id']) for a in methods}) for r in cohort]
    metrics=evaluate_scope(cohort,predictions,methods,[('baseline',a) for a in methods if a!='baseline']+([('refresh48','wide_candidates')] if 'refresh48' in methods else []))
    gates={a:gate_statistics(rows,'baseline',a) for a in methods if a not in ('baseline','refresh48')}
    if 'wide_candidates' in gates:
        refresh=gate_statistics(rows,'refresh48','wide_candidates')
        gates['wide_candidates']['refresh48_control']=refresh
        gates['wide_candidates']['statistical_gate'] &= refresh['checks']['complete'] and refresh['checks']['net_gain'] and refresh['checks']['author_directions']
    structure=[]
    for x in inputrows:
        b=x['retrieval']['baseline']
        for arm,r in x['retrieval'].items():
            if arm=='baseline':continue
            structure.append(dict(case_id=x['case_id'],proposition_id=x['proposition_id'],arm=arm,
                same_reference=r['reference']==b['reference'],lost_ids=sorted(set(b['selected_ids'])-set(r['selected_ids'])),
                added_ids=sorted(set(r['selected_ids'])-set(b['selected_ids'])),selected_ids=r['selected_ids'],
                body_characters=r['body_characters'],selector_status=r.get('selector_status'),repairs=r.get('repairs',[])))
    out=output or s.OUT/'screen_analysis_001';out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_json(out/'metrics.json',metrics);s.pilot.write_json(out/'mechanical_gates.json',gates)
    s.pilot.write_csv(out/'transitions.csv',rows);s.pilot.write_jsonl(out/'transitions.jsonl',rows)
    s.pilot.write_jsonl(out/'normalized_responses.jsonl',list(normalized.values()));s.pilot.write_json(out/'repeat_diagnostics.json',repeats)
    s.pilot.write_jsonl(out/'input_differences.jsonl',structure);s.pilot.write_csv(out/'attempts.csv',attempts)
    for a,p in predictions.items():s.pilot.write_csv(out/f'predictions_{a}.csv',p,fields=['proposition_id','verdict'])
    summary=dict(claims=len(cohort),valid_predictions={a:len(p) for a,p in predictions.items()},repeat_pairs=len(repeats),repeat_changes=sum(r['changed'] for r in repeats),
        statistical_candidates=[a for a,g in gates.items() if g['statistical_gate']],
        all_task_cost_or_reserved_cny=sum(s.read_json(s.OUT/'live'/phase/'state.json')['used_or_reserved_cny'] for phase in ('unit_aux','unit_judge','screen_aux','screen_judge')),
        cost_scope='four stages through screening only; later combination/confirmation never retroactively included',new_methods_not_confirmed=True)
    s.pilot.write_json(out/'summary.json',summary)
    # Final gate and freeze follow actual input/output mechanism review.
    print(s.pilot.canonical(summary));print(s.pilot.canonical({a:dict(net=g['net'],checks=g['checks']) for a,g in gates.items()}))

if __name__=='__main__':
    from pathlib import Path
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args();run(a.output)
