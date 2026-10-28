"""CPU analysis of107 first receipts; no model calls, relabeling or postprocessing."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
import numpy as np
import common107 as c
sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'))
from parse105 import parse
from evaluate105 import metric,cohort,preds
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import paired_compare
from run107 import verify_bundle


def collect(folder,expected,bundle_sha,arm,batches):
    records={};seconds=0.;output_tokens=0
    for path in sorted(Path(folder).glob('batch-*.json')):
        if '.inflight.' in path.name:continue
        saved=c.read(path);number=int(path.stem.split('-')[-1])
        if number not in batches or saved['ids']!=batches[number] or saved['bundle_sha256']!=bundle_sha:raise ValueError('Batch differs from frozen input/order/package')
        if saved['ids']!=[r['id'] for r in saved['records']] or saved.get('aux_head_used',False):raise ValueError('Record order or inference interface differs')
        seconds+=saved['batch_seconds']
        for row in saved['records']:
            identifier=row['id']
            if row.get('arm')!=arm or identifier not in expected or identifier in records:raise ValueError('Wrong arm, duplicate or out-of-panel result')
            if row['prompt_token_sha256']!=expected[identifier]['prompt_token_sha256']:raise ValueError('Prompt token SHA differs')
            records[identifier]=dict(row,parsed=parse(row['content'],row['finish_reason']));output_tokens+=row['output_tokens']
    return records,dict(generation_seconds=seconds,output_tokens=output_tokens,received=len(records))


def cover(keys,records):
    good=[r for r in keys if r['id'] in records and records[r['id']]['parsed']['valid']];goodids={r['id'] for r in good}
    n=len(keys);nonS=sum(r['GT']!='Supported' for r in keys)
    correct=sum(records[r['id']]['parsed']['verdict']==r['GT'] for r in good)
    false=sum(r['GT']!='Supported' and records[r['id']]['parsed']['verdict']=='Supported' for r in good)
    unknown=sum(r['GT']!='Supported' and r['id'] not in goodids for r in keys)
    invalid=[dict(id=r['id'],sid=r['sid'],GT=r['GT'],reason=records[r['id']]['parsed'].get('reason'),finish_reason=records[r['id']]['finish_reason']) for r in keys if r['id'] in records and not records[r['id']]['parsed']['valid']]
    return dict(frozen_N=n,received=sum(r['id'] in records for r in keys),valid=len(good),invalid=len(invalid),
        missing=sum(r['id'] not in records for r in keys),invalid_details=invalid,PA_full_bounds=[correct/n,(correct+n-len(good))/n],
        false_S_observed=false,non_S=nonS,false_S_full_bounds=[false/nonS,(false+unknown)/nonS] if nonS else None)


def metrics(rows,arm,profile='research_patient'):
    return metric(rows,arm,profile=profile) if rows else None


def risk_deltas(rows,baseline,candidate):
    """Explicit undefined denominators, including a missing/invalid entire class."""
    subjects=sorted({r['sid'] for r in rows});by={sid:[r for r in rows if r['sid']==sid] for sid in subjects}
    def value(part,kind,arm):
        actual=[r for r in part if (r['GT']!='Supported' if kind=='false_S_rate' else r['GT']==kind)]
        if not actual:return None
        return sum(r['pred'][arm]==('Supported' if kind=='false_S_rate' else kind) for r in actual)/len(actual)
    result={}
    for name,kind in [('false_S_rate','false_S_rate'),('S_recall','Supported'),('NS_recall','Not Supported'),('NA_recall','Not Addressed')]:
        a=value(rows,kind,baseline);b=value(rows,kind,candidate)
        if a is None or len(subjects)<2:
            result[name]=dict(delta=None if a is None else b-a,ci95=None,valid_draws=0,undefined_denominator=a is None)
            continue
        draws=[]
        for seed in range(1000):
            sample=[r for i in np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True) for r in by[subjects[i]]]
            x=value(sample,kind,baseline);y=value(sample,kind,candidate)
            if x is not None:draws.append(y-x)
        result[name]=dict(delta=b-a,ci95=np.percentile(draws,[2.5,97.5]).tolist() if draws else None,valid_draws=len(draws),undefined_denominator=False)
    return result


def compare(rows):
    baseline='label_only';candidate='support_aux';subjects=sorted({r['sid'] for r in rows})
    byclass={label:dict(N=sum(r['GT']==label for r in rows),
        rescued=sum(r['GT']==label and r['pred'][baseline]!=r['GT']==r['pred'][candidate] for r in rows),
        harmed=sum(r['GT']==label and r['pred'][baseline]==r['GT']!=r['pred'][candidate] for r in rows)) for label in c.LABELS}
    risk=risk_deltas(rows,baseline,candidate);by={sid:[r for r in rows if r['sid']==sid] for sid in subjects}
    transitions={gt:{before:{after:sum(r['GT']==gt and r['pred'][baseline]==before and r['pred'][candidate]==after for r in rows) for after in c.LABELS} for before in c.LABELS} for gt in c.LABELS}
    patient=[]
    for sid,part in by.items():
        patient.append(dict(sid=sid,N=len(part),correct_delta=sum(int(r['pred'][candidate]==r['GT'])-int(r['pred'][baseline]==r['GT']) for r in part),
            false_S_delta=sum(int(r['GT']!='Supported' and r['pred'][candidate]=='Supported')-int(r['GT']!='Supported' and r['pred'][baseline]=='Supported') for r in part),
            supported_predictions_delta=sum(int(r['pred'][candidate]=='Supported')-int(r['pred'][baseline]=='Supported') for r in part)))
    return dict(primary=paired_compare(cohort(rows),preds(rows,baseline),preds(rows,candidate)) if len(subjects)>=2 else None,
        evidence_insufficient=len(subjects)<2,reason='fewer_than_two_common_valid_patients' if len(subjects)<2 else None,
        risk=risk,by_true_class=byclass,
        false_S_new=sum(r['GT']!='Supported' and r['pred'][baseline]!='Supported' and r['pred'][candidate]=='Supported' for r in rows),
        false_S_avoided=sum(r['GT']!='Supported' and r['pred'][baseline]=='Supported' and r['pred'][candidate]!='Supported' for r in rows),
        predicted_S={arm:sum(r['pred'][arm]=='Supported' for r in rows) for arm in c.ARMS},
        by_GT_prediction_transitions=transitions,patients=patient,
        fewer_S_alone_does_not_prove_better_verification=True)


def evaluate_run(bundle,results,output):
    bundle=Path(bundle);results=Path(results);verify_bundle(bundle);bundle_sha=c.sha(bundle/'manifest.json')
    keys=c.rows(bundle/'frozen/eval_keys.jsonl');expected={r['id']:r for r in c.rows(bundle/'frozen/eval_token_lengths.jsonl')}
    batches={r['batch']:r['ids'] for r in c.read(bundle/'frozen/eval_batches.json')['batches']};data={};cost={}
    for arm in c.ARMS:data[arm],cost[arm]=collect(results/'eval'/arm/'development',expected,bundle_sha,arm,batches)
    panels={}
    for panel in ('natural','pressure'):
        full=[r for r in keys if r['panel']==panel]
        common=[dict(r,pred={**{arm:data[arm][r['id']]['parsed']['verdict'] for arm in c.ARMS},'paper_r1':r['paper_r1']}) for r in full
            if all(r['id'] in data[arm] and data[arm][r['id']]['parsed']['valid'] for arm in c.ARMS)]
        panels[panel]=dict(frozen_N=len(full),common_valid_N=len(common),common_ids=[r['id'] for r in common],
            metrics={arm:metrics(common,arm) for arm in (*c.ARMS,'paper_r1')},paired=compare(common),
            full_N_coverage={arm:cover(full,data[arm]) for arm in c.ARMS},
            author={author:{arm:metrics([r for r in common if r['author']==author],arm,profile='none') for arm in (*c.ARMS,'paper_r1')}
                for author in ('human','llm') if any(r['author']==author for r in common)})
    complete=all(p['full_N_coverage'][arm]['missing']==0 for p in panels.values() for arm in c.ARMS)
    training={}
    for arm in c.ARMS:
        folder=results/'train'/arm;steps=c.rows(folder/'steps.jsonl') if (folder/'steps.jsonl').exists() else []
        # A crash after checkpoint commit but before logging can leave a gap;
        # checkpoint cursor determines completion, logs only observed costs.
        numbers=[r['step'] for r in steps];duplicates=sorted({s for s in numbers if numbers.count(s)>1})
        missing=sorted(set(range(1,51))-set(numbers));unexpected=sorted(set(numbers)-set(range(1,51)))
        training[arm]=dict(observed_step_records=len(steps),unique_step_records=len(set(numbers)),duplicate_steps=duplicates,
            missing_step_logs=missing,unexpected_steps=unexpected,cost_log_complete=not(duplicates or missing or unexpected),
            logged_seconds_include_all_observed_records_even_duplicates=True,logged_training_seconds=sum(r['seconds'] for r in steps),
            logged_checkpoint_seconds=sum(r['checkpoint_seconds'] for r in steps),
            done=c.read(folder/'training_done.json') if (folder/'training_done.json').exists() else None)
    ledger=c.read(results/'compute107.json') if (results/'compute107.json').exists() else None
    result=dict(task=107,panels=panels,inference_cost=cost,training=training,billing_ledger=ledger,
        all_frozen_first_requests_received=complete,primary_contrast='fresh_label_only_vs_fresh_support_aux',
        evidence_insufficient=not complete or any(p['paired']['evidence_insufficient'] for p in panels.values()),
        primary_common_ids_recomputed_for107=True,natural_and_pressure_never_pooled=True,missing_invalid_no_fallback=True,
        paper_r1_historical_only=True,current_same_model_verifact_ref_not_run=True,auxiliary_head_never_used_at_inference=True,
        bootstrap='1000 paired patient clusters; does not cover seed/retraining/development exposure/new hospitals',
        automatic_upgrade=False,new_API_calls=0,
        research_decision_requires_joint_MCC_false_S_PA_class_recall_assessment=True,
        no_posthoc_weight_threshold_sampling_epoch_tuning_authorized=True)
    c.put(output,result)
    print(c.canonical(dict(output=str(output),common_valid={p:r['common_valid_N'] for p,r in panels.items()},all_requests_received=complete)))
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','results','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();evaluate_run(a.bundle,a.results,a.output)


if __name__=='__main__':main()
