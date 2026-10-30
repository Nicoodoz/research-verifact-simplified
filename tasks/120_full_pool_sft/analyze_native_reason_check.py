"""Parse native reason receipts; semantic judgments must be supplied explicitly."""
from pathlib import Path
from collections import Counter
import argparse,sys
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'.local_models/120_full_pool_sft/native_reason_check'
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as c
from native_reason_check import parse_pair


def main():
    p=argparse.ArgumentParser();p.add_argument('--reviews',type=Path);a=p.parse_args()
    job=c.read(P/'job.json');meta={r['id']:r for r in c.rows(P/'metadata.jsonl')}
    source={r['id']:r for r in c.rows(P/'bundle/data/native_reason_check/inputs.jsonl')}
    checked={r['id'] for r in c.rows(P/'grounding6_inputs.jsonl')}
    reviews={} if a.reviews is None else {(r['id'],r['arm']):r for r in c.rows(a.reviews)}
    if a.reviews and len(reviews)!=len(c.rows(a.reviews)):raise ValueError('Duplicate semantic review')
    public=[];private=[];summary=dict(scope='20 purposeful native-output diagnostic cases, not population accuracy',
        original_GT_unchanged=True,no_training=True,no_old_reason_reuse=True,
        original_full_reference=True,all_outputs_first_receipts=True,source_review_cases=len(checked),
        main120_results_unchanged=True,models={})
    summary['historical_paper_r1']=dict(N=len(meta),correct_to_original_GT_N=sum(r['paper_r1']==r['GT'] for r in meta.values()),
        generated_in_this_task=False,reason_requested_in_this_task=False)
    summary['review_scope']=dict(reviewer='Codex root AI-assisted review, not independent physician certification',
        consistency='Reason must justify its own verdict; unresolved scope or class-boundary inference is unclear.',
        grounding='Does the actual supplied reference support the reason facts and relation? OriginalGT agreement is a separate axis.',
        full_source6_selected_before_outputs=True,unreviewed_other_sources=14)
    for arm in job['arms']:
        rows=[]
        for identifier in job['ids']:
            path=P/'evidence'/arm['name']/(identifier+'.json')
            if not path.exists():continue
            r=c.read(path);parsed=parse_pair(r['content'],r['finish_reason'])
            if r['parsed']!=parsed:raise ValueError('Original parser result changed')
            if (r['id'],r['arm'],r['adapter_sha256'],r['prompt_token_sha256'])!=(identifier,arm['name'],arm['adapter_sha256'],source[identifier]['expected_prompt_sha256']):
                raise ValueError('Source model/prompt differs')
            expected_state='all_disabled' if arm['mode']=='base' else arm['name']
            if r['adapter_state']!=expected_state:raise ValueError('Unexpected adapter activation')
            semantic=reviews.get((identifier,arm['name']),{})
            consistency=semantic.get('consistency','unreviewed')
            grounding=semantic.get('grounding','not_reviewed')
            if consistency not in ('consistent','inconsistent','unclear','not_evaluable','unreviewed'):
                raise ValueError('Unknown reason/verdict review category')
            if grounding not in ('supported','unsupported_detail','contradicted','ambiguous','not_reviewed','not_evaluable'):
                raise ValueError('Unknown source-grounding category')
            if identifier not in checked and grounding not in ('not_reviewed','not_evaluable'):
                raise ValueError('Do not claim full-reference review beyond the fixed6')
            row=dict(id=identifier,arm=arm['name'],GT=meta[identifier]['GT'],
                verdict=parsed['verdict'],label_valid=parsed['label_parse_valid'],
                pair_valid=parsed['diagnostic_pair_valid'],finish_reason=r['finish_reason'],
                reason_present=bool(parsed['reason']),reason_verdict_consistency=consistency,
                source_grounding=grounding,in_fixed_source6=identifier in checked,
                input_tokens=r['input_tokens'],output_tokens=r['output_tokens'],seconds=r['seconds'])
            rows.append(row);public.append(row)
            private.append(dict(row,claim=source[identifier]['claim'],reason=parsed['reason'],
                review_note=semantic.get('note'),source_path=str(path)))
        summary['models'][arm['name']]=dict(expected_N=20,received_N=len(rows),missing_N=20-len(rows),
            label_valid_N=sum(r['label_valid'] for r in rows),pair_valid_N=sum(r['pair_valid'] for r in rows),
            correct_to_original_GT_N=sum(r['label_valid'] and r['verdict']==r['GT'] for r in rows),
            consistency=dict(Counter(r['reason_verdict_consistency'] for r in rows)),
            fixed6_grounding=dict(Counter(r['source_grounding'] for r in rows if r['in_fixed_source6'])),
            total_seconds=sum(r['seconds'] for r in rows))
    expected={(i,x['name']) for i in job['ids'] for x in job['arms']}
    if not set(reviews)<=expected:raise ValueError('Review outside frozen20/three models')
    if a.reviews and set(reviews)!={(r['id'],r['arm']) for r in public}:
        raise ValueError('Every received first output needs an explicit review status')
    c.putl(P/'reason_review_queue.jsonl',private)
    c.put(ROOT/'outputs/120_full_pool_sft/native_reason_diagnostic.json',summary)
    c.putl(ROOT/'outputs/120_full_pool_sft/native_reason_predictions_sanitized.jsonl',public)
    print(c.canonical(summary))


if __name__=='__main__':main()
