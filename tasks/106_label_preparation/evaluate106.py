"""CPU-only scoring of the frozen future experiment, never run target models.

The primary contrast uses the TWO LOSS ARMS' common valid IDs; only sum is newly trained. A
separate three-arm table keeps all old baseline invalid/truncated answers and
cannot make their missingness disappear. Diagnosis uses its own training IDs.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import numpy as np
import common106 as c
sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
from parse105 import parse
from evaluate105 import metric,cohort,preds,risk_deltas
from run106 import verify_bundle
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import paired_compare

ARMS=('base_judge','label_mean','label_sum')

def development_decision(panels):
    """Frozen descriptive tradeoff gate, never upgrades or starts a new task."""
    n=panels['natural'];p=panels['pressure'];a=n['primary_metrics']['label_mean'];b=n['primary_metrics']['label_sum']
    pa=p['primary_metrics']['label_mean'];pb=p['primary_metrics']['label_sum']
    delta=dict(natural_MCC=b['mcc']-a['mcc'],natural_PA=b['percent_agreement']-a['percent_agreement'],natural_false_S=b['false_S']-a['false_S'],
        pressure_MCC=pb['mcc']-pa['mcc'],pressure_false_S=pb['false_S']-pa['false_S'])
    for label in c.LABELS:delta['natural_'+label+'_recall']=b['per_class'][label]['recall']-a['per_class'][label]['recall']
    for label in c.LABELS[1:]:delta['pressure_'+label+'_recall']=pb['per_class'][label]['recall']-pa['per_class'][label]['recall']
    complete=all(panel['full_N_coverage'][arm]['received']==panel['frozen_N'] and panel['full_N_coverage'][arm]['missing']==0 for panel in panels.values() for arm in ('label_mean','label_sum'))
    enough=all(panel['primary_training_arms_common_N']/panel['frozen_N']>=.95 for panel in panels.values())
    guards=dict(natural_PA=delta['natural_PA']>=-.02-1e-12,natural_S_recall=delta['natural_Supported_recall']>=-.02-1e-12,
        natural_NS_recall=delta['natural_Not Supported_recall']>=-.05-1e-12,natural_NA_recall=delta['natural_Not Addressed_recall']>=-.05-1e-12,
        pressure_NS_recall=delta['pressure_Not Supported_recall']>=-.05-1e-12,pressure_NA_recall=delta['pressure_Not Addressed_recall']>=-.05-1e-12,
        pressure_MCC=delta['pressure_MCC']>=-.02-1e-12,pressure_false_S=delta['pressure_false_S']<=2)
    paths=dict(quality_led=delta['natural_MCC']>=.02-1e-12 and delta['natural_false_S']<=1,
               risk_led=delta['natural_false_S']<=-4 and delta['natural_MCC']>=-.01-1e-12)
    # Recompute the frozen105 mean model on the exact primary common IDs.
    # Under the declared cache conditions it is the same196 objective control;
    # the historical alias also supplies a fixed usability floor on rerun.
    hn=n['primary_metrics']['historical_label_only196'];hp=p['primary_metrics']['historical_label_only196']
    anchor=dict(natural_PA=b['percent_agreement']>=hn['percent_agreement']-.02-1e-12,
        natural_S_recall=b['per_class']['Supported']['recall']>=hn['per_class']['Supported']['recall']-.02-1e-12)
    for panel,newm,hist in [('natural',b,hn),('pressure',pb,hp)]:
        for label in c.LABELS[1:]:anchor[panel+'_'+label+'_recall']=newm['per_class'][label]['recall']>=hist['per_class'][label]['recall']-.05-1e-12
        for label in c.LABELS:
            recall=newm['per_class'][label]['recall']
            if recall is not None:anchor[panel+'_'+label+'_nonzero_recall']=recall>0
    eligible=complete and enough and all(guards.values()) and all(anchor.values()) and any(paths.values())
    return dict(delta=delta,all_fixed_new_arm_requests_received=complete,pair_coverage_each_panel_at_least95pct=enough,guards=guards,paths=paths,
        historical105_label196_usability_guards=anchor,frozen105_mean_is_same196_objective_control=True,
        worth_separately_authorized_confirmation_development=eligible,
        status='execution_incomplete' if not(complete and enough) else ('development_point_gate_met' if eligible else 'development_point_gate_not_met'),
        point_gate_not_stable_superiority=True,not_paper_confirmation=True,automatic_upgrade=False)

def collect(folder,expected,bundle_sha,expected_arm,expected_batches):
    records={}
    for path in sorted(Path(folder).glob('batch-*.json')):
        if '.inflight.' in path.name:continue
        batch=c.read(path)
        number=int(path.stem.split('-')[-1])
        if number not in expected_batches or batch['ids']!=expected_batches[number]:raise ValueError('Result batch differs from frozen batch composition/order')
        if batch['bundle_sha256']!=bundle_sha:raise ValueError('Result belongs to a different frozen bundle')
        if batch['ids']!=[r['id'] for r in batch['records']]:raise ValueError('Batch record order mismatch')
        for row in batch['records']:
            if row.get('arm')!=expected_arm:raise ValueError('Result stored under the wrong arm directory')
            if row['id'] in records or row['id'] not in expected:raise ValueError('Duplicate or out-of-panel ID')
            if row['prompt_token_sha256']!=expected[row['id']]['prompt_token_sha256']:raise ValueError('Inference input SHA mismatch')
            records[row['id']]=dict(row,parsed=parse(row['content'],row['finish_reason']))
    return records

def cover(keys,records):
    good=[r for r in keys if r['id'] in records and records[r['id']]['parsed']['valid']]
    goodids={r['id'] for r in good};N=len(keys);nonS=sum(r['GT']!='Supported' for r in keys)
    correct=sum(records[r['id']]['parsed']['verdict']==r['GT'] for r in good)
    false=sum(r['GT']!='Supported' and records[r['id']]['parsed']['verdict']=='Supported' for r in good)
    unknown_nonS=sum(r['GT']!='Supported' and r['id'] not in goodids for r in keys)
    return dict(frozen_N=N,received=sum(r['id'] in records for r in keys),valid=len(good),
                invalid=sum(r['id'] in records and not records[r['id']]['parsed']['valid'] for r in keys),
                missing=sum(r['id'] not in records for r in keys),PA_full_bounds=[correct/N,(correct+N-len(good))/N],
                false_S_observed=false,non_S=nonS,false_S_full_bounds=[false/nonS,(false+unknown_nonS)/nonS] if nonS else None)

def validate_path_score(score):
    if set(score['complete_JSON_EOS_sum_logP'])!=set(c.LABELS) or set(score['restricted_legal_q'])!=set(c.LABELS):raise ValueError('All three complete label paths required')
    logs=np.array([score['complete_JSON_EOS_sum_logP'][label] for label in c.LABELS],dtype=float)
    q=np.array([score['restricted_legal_q'][label] for label in c.LABELS],dtype=float)
    if not np.isfinite(logs).all() or (logs>0).any() or not np.isfinite(q).all() or (q<0).any() or (q>1).any():raise ValueError('Nonfinite or out-of-range diagnostic probability')
    expected=np.exp(logs-logs.max());expected/=expected.sum()
    if not np.allclose(q,expected,atol=1e-7,rtol=1e-6) or abs(q.sum()-1)>1e-6 or score['restricted_legal_MAP']!=c.LABELS[int(expected.argmax())]:raise ValueError('Path-q or MAP disagrees with complete log probabilities')
    branch=score['first_value_branch_raw_full_vocab_probabilities']
    if set(branch)!={'S_token','Not_token'} or not all(np.isfinite(v) and 0<=v<=1 for v in branch.values()) or sum(branch.values())>1+1e-6:raise ValueError('Invalid raw first-branch probabilities')
    return True

def joined(keys,data,arms):
    return [dict(row,pred={**{arm:data[arm][row['id']]['parsed']['verdict'] for arm in arms},'paper_r1':row['paper_r1'],
                          'historical_label_only196':data['historical_label_only196'][row['id']]['parsed']['verdict']}) for row in keys
            if all(row['id'] in data[arm] and data[arm][row['id']]['parsed']['valid'] for arm in arms)]

def compare(rows,baseline,candidate):
    if len({r['sid'] for r in rows})<2:raise ValueError('Too few paired patients to score a completed experiment')
    byclass={label:dict(rescued=sum(r['GT']==label and r['pred'][baseline]!=r['GT']==r['pred'][candidate] for r in rows),
                              harmed=sum(r['GT']==label and r['pred'][baseline]==r['GT']!=r['pred'][candidate] for r in rows)) for label in c.LABELS}
    risk=risk_deltas(rows,baseline,candidate)
    subjects=sorted({r['sid'] for r in rows});by={sid:[r for r in rows if r['sid']==sid] for sid in subjects}
    def sdelta(part):
        actual=[r for r in part if r['GT']=='Supported']
        if not actual:return None
        return sum((r['pred'][candidate]=='Supported')-(r['pred'][baseline]=='Supported') for r in actual)/len(actual)
    point=sdelta(rows)
    if point is None:risk['S_recall']=dict(delta=None,ci95=None,valid_draws=0)
    else:
        draws=[sdelta([r for i in np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True) for r in by[subjects[i]]]) for seed in range(1000)]
        valid=[v for v in draws if v is not None]
        risk['S_recall']=dict(delta=point,ci95=np.percentile(valid,[2.5,97.5]).tolist(),valid_draws=len(valid))
    return dict(primary=paired_compare(cohort(rows),preds(rows,baseline),preds(rows,candidate)),risk=risk,
                by_true_class=byclass,false_S_new=sum(r['GT']!='Supported' and r['pred'][baseline]!='Supported' and r['pred'][candidate]=='Supported' for r in rows),
                false_S_avoided=sum(r['GT']!='Supported' and r['pred'][baseline]=='Supported' and r['pred'][candidate]!='Supported' for r in rows))

def evaluate_run(bundle,results,output):
    bundle=Path(bundle);results=Path(results);output=Path(output);verify_bundle(bundle);bundle_sha=c.sha(bundle/'manifest.json')
    keys=c.rows(bundle/'frozen/eval_keys.jsonl');expected={r['id']:r for r in c.rows(bundle/'frozen/eval_token_lengths.jsonl')}
    batches={r['batch']:r['ids'] for r in c.read(bundle/'frozen/eval_batches.json')['batches']}
    data={arm:collect(results/'eval'/arm/'development',expected,bundle_sha,arm,batches) for arm in ARMS}
    historical=c.rows(bundle/'frozen/105_label_only_cached.jsonl')
    if len(historical)!=len(keys) or any(not r['parsed']['valid'] or r['prompt_token_sha256']!=expected[r['id']]['prompt_token_sha256'] for r in historical):raise ValueError('Historical quality-anchor cache changed or incomplete')
    data['historical_label_only196']={r['id']:r for r in historical}
    if not data['base_judge'] or not data['label_mean']:
        # Runtime eligibility was already enforced before any worker started.
        # Also verify all observed future GPU loads against the frozen family.
        authorization=c.read(results/'compute106.json')
        if authorization.get('baseline_cache_mode')!='reuse':raise ValueError('Required new baseline500 missing; never silently fall back to105')
        loads=c.rows(results/'loads.jsonl');expected_gpu=c.read(bundle/'frozen/expected_runtime105.json')['GPU_name']
        if not loads or any(r['gpu']!=expected_gpu for r in loads):raise ValueError('Baseline cache invalid: current GPU identity differs')
        pre=c.read(results/'preflight106.json')
        if pre['bundle_sha256']!=bundle_sha or not pre['tokenizer_bridge_verified']:raise ValueError('No current version/token bridge for baseline cache')
        for arm,filename in [('base_judge','base_judge_cached.jsonl'),('label_mean','label_mean_cached.jsonl')]:
            if not data[arm]:data[arm]={r['id']:r for r in c.rows(bundle/'frozen'/filename)}
    panels={}
    for panel in ('natural','pressure'):
        full=[r for r in keys if r['panel']==panel]
        primary=joined(full,data,('label_mean','label_sum'));secondary=joined(full,data,ARMS)
        panels[panel]=dict(frozen_N=len(full),primary_training_arms_common_N=len(primary),three_arm_common_N=len(secondary),
            primary_metrics={arm:metric(primary,arm) for arm in ('label_mean','label_sum','historical_label_only196','paper_r1')},
            primary_comparison=compare(primary,'label_mean','label_sum'),
            three_arm_metrics={arm:metric(secondary,arm) for arm in (*ARMS,'historical_label_only196','paper_r1')},
            three_arm_comparisons={arm:compare(secondary,'base_judge',arm) for arm in ('label_mean','label_sum')},
            full_N_coverage={arm:cover(full,data[arm]) for arm in ARMS},
            author={author:{arm:metric([r for r in primary if r['author']==author],arm,profile='none') for arm in ('label_mean','label_sum','historical_label_only196','paper_r1')}
                    for author in ('human','llm') if any(r['author']==author for r in primary)})
    diag_map={r['id']:r for r in c.rows(bundle/'frozen/diagnostic_token_lengths.jsonl')}
    diag_batches={r['batch']:r['ids'] for r in c.read(bundle/'frozen/diagnostic_batches.json')['batches']}
    diagnostic={arm:collect(results/'eval'/arm/'diagnostic',diag_map,bundle_sha,arm,diag_batches) for arm in ARMS}
    diagnostic_summary={}
    for arm in ('label_mean','label_sum'):
        manifest=[r for r in c.rows(bundle/'frozen/diagnostic_manifest.jsonl') if r['arm']==arm]
        diagnostic_summary[arm]={}
        for label in c.LABELS:
            rows=[r for r in manifest if r['GT']==label]
            diagnostic_summary[arm][label]={key:dict(N=len(rows),received=sum(r['id'] in diagnostic[key] for r in rows),
                valid=sum(r['id'] in diagnostic[key] and diagnostic[key][r['id']]['parsed']['valid'] for r in rows),
                correct=sum(r['id'] in diagnostic[key] and diagnostic[key][r['id']]['parsed']['verdict']==r['GT'] for r in rows)) for key in ('base_judge',arm)}
    diagnostic_scores=[]
    diag_truth={r['id']:r for r in c.rows(bundle/'frozen/diagnostic_manifest.jsonl')}
    for arm in ARMS:
        scores=[]
        for path in sorted((results/'eval'/arm/'diagnostic/complete_label_paths').glob('*.json')):
            score=c.read(path);identifier=score['id']
            if score['arm']!=arm or identifier not in diag_map or score['bundle_sha256']!=bundle_sha or score['prompt_token_sha256']!=diag_map[identifier]['prompt_token_sha256']:raise ValueError('Diagnostic score identity mismatch')
            validate_path_score(score)
            raw=diagnostic[arm].get(identifier)
            greedy=raw['parsed']['verdict'] if raw else None
            scores.append(dict(score,GT=diag_truth[identifier]['GT'],free_greedy=greedy,greedy_valid=bool(raw and raw['parsed']['valid']),
                greedy_differs_from_complete_path_MAP=greedy is not None and greedy!=score['restricted_legal_MAP']))
        if len({r['id'] for r in scores})!=len(scores):raise ValueError('Duplicate diagnostic path scores')
        diagnostic_scores.extend(scores)
        diagnostic_summary[arm+'_complete_path_scores']=dict(expected=len(diag_map),received=len(scores),
            free_greedy_MAP_disagreements=sum(r['greedy_differs_from_complete_path_MAP'] for r in scores),
            complete_path_MAP_correct=sum(r['restricted_legal_MAP']==r['GT'] for r in scores),
            formal_evaluation_still_free_greedy=True)
    diagnostic_complete=all(len(diagnostic[arm])==len(diag_map) and diagnostic_summary[arm+'_complete_path_scores']['received']==len(diag_map) for arm in ARMS)
    decision=development_decision(panels)
    decision['diagnostic_outputs_complete']=diagnostic_complete
    decision['point_gate_before_diagnostic_completeness']=decision['worth_separately_authorized_confirmation_development']
    if not diagnostic_complete:
        decision['worth_separately_authorized_confirmation_development']=False;decision['status']='execution_incomplete'
    runtime_loads=c.rows(results/'loads.jsonl')
    non_strict=any(r.get('training_hardware_comparison')=='non_strict_training_hardware_comparison' for r in runtime_loads)
    result=dict(task=106,panels=panels,training_diagnostics=diagnostic_summary,training_diagnostics_not_generalization=True,
                training_hardware_comparison='non_strict_training_hardware_comparison' if non_strict else 'same_GPU_family_and_pinned_backend',
                inference_rerun_does_not_retrain_control=True,
                training_diagnostic_scores=diagnostic_scores,first_branch_not_three_class_probability=True,
                development_decision=decision,diagnostic_outputs_complete=diagnostic_complete,
                primary_two_loss_arms=True,only_one_new_training=True,baseline_invalid_retained=True,missing_invalid_no_fallback=True,paper_r1_historical_only=True,
                bootstrap='1000 paired patient clusters; not historical selection/retraining/new hospital uncertainty',
        active_contrast='same196_label_mean_vs_global_normalized_label_sum',only_new_training='label_sum',
        automatic_upgrade=False,new_model_calls=0)
    c.put(output,result);print(c.canonical(dict(output=str(output),primary_N={p:r['primary_training_arms_common_N'] for p,r in panels.items()})))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--results',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();evaluate_run(a.bundle,a.results,a.output)

if __name__=='__main__':main()
