"""Label sensitivity to explicit reference removal; not a new clinical score."""
from pathlib import Path
import argparse
from collections import Counter
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/120_full_pool_sft'))
from analyze120 import collect
from final_compare120 import lookup,metrics,LABELS
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as common


def summarize(keys,full,empty):
    valid=[r for r in keys if full[r['id']].get('valid') is True
           and empty.get(r['id'],{}).get('valid') is True]
    old={r['id']:full[r['id']]['verdict'] for r in valid}
    new={r['id']:empty[r['id']]['verdict'] for r in valid}
    counts=Counter((old[r['id']],new[r['id']]) for r in valid)
    return dict(expected_N=len(keys),new_received_N=len(empty),paired_valid_N=len(valid),
        new_missing_N=sum(r['id'] not in empty for r in keys),
        new_invalid_N=sum(r['id'] in empty and not empty[r['id']].get('valid') for r in keys),
        unchanged_N=sum(old[r['id']]==new[r['id']] for r in valid),
        full_NA_N=sum(v=='Not Addressed' for v in old.values()),empty_NA_N=sum(v=='Not Addressed' for v in new.values()),
        transition_matrix=[[counts[a,b] for b in LABELS] for a in LABELS],
        full_with_original_GT=metrics(valid,old) if valid else None,
        empty_with_original_GT_diagnostic_only=metrics(valid,new) if valid else None,
        full_predictions_not_used_to_fill_missing=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private',type=Path,default=ROOT/'.local_models/129_native_reference_check')
    a=parser.parse_args();P=a.private
    choice=common.read(P/'choice.json');keys=common.rows(P/'analysis_keys.jsonl')
    if len(keys)!=160 or len({r['id'] for r in keys})!=160:raise ValueError('Frozen160 changed')
    base=lookup(ROOT/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')
    candidate=lookup(Path(choice['source_predictions']))
    frames={'107':base,choice['candidate_name']:candidate}
    jobs={'107':'reference_blank107',choice['candidate_name']:'reference_blank_native'}
    rows=[];report=dict(task=129,purpose='input sensitivity, not a deployable method',
        candidate=choice['candidate_name'],original_GT_unchanged=True,full_context_outputs_reused=True,
        no_new_training=True,models={},label_order=list(LABELS),
        limits=['Original GT concerns the real full-EHR claim; it is not newly assigned empty-reference gold.',
                'Sensitivity to reference removal does not certify medical reasoning or evidence localization.'])
    expected={r['id']:r for r in keys}
    for name,folder in jobs.items():
        empty={r['id']:r for r in collect([P/'evidence'/folder])}
        if not set(empty)<=set(expected):raise ValueError('Unexpected diagnostic ID')
        for i,r in empty.items():
            if r['source_prompt_sha256_104']!=expected[i]['empty_prompt_sha256']:
                raise ValueError('Not the frozen empty-reference prompt')
            expected_adapter=('096f30c4d1885d2a9775f5390a0de24c214f430fc3b1fa1b507d901e7619f3f8'
                              if name=='107' else choice['adapter_sha256'])
            if r['source_adapter_sha256']!=expected_adapter:
                raise ValueError('Diagnostic model identity differs')
        report['models'][name]=summarize(keys,frames[name],empty)
        report['models'][name]['by_original_GT']={label:summarize(
            [r for r in keys if r['GT']==label],frames[name],
            {i:r for i,r in empty.items() if expected[i]['GT']==label}) for label in LABELS}
        for r in keys:
            i=r['id'];new=empty.get(i)
            rows.append(dict(id=i,sid=str(r['sid']),GT=r['GT'],old_panel=r['old_panel'],model=name,
                full_verdict=frames[name][i]['verdict'],empty_verdict=new['verdict'] if new else None,
                empty_valid=new['valid'] if new else False,empty_missing=new is None))
    out=ROOT/'outputs/129_native_reference_check'
    common.put(out/'results.json',report);common.putl(out/'predictions_sanitized.jsonl',rows)
    print(common.canonical({k:{x:v[x] for x in ('expected_N','paired_valid_N','unchanged_N','full_NA_N','empty_NA_N')} for k,v in report['models'].items()}))


if __name__=='__main__':main()
