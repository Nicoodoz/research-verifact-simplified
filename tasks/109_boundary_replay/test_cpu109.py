"""Necessary new sampling/decision boundary checks; no model or CUDA imports."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
import common109 as c
from select109 import choose_hard,supported_request,select,load_predictions,InsufficientData
from run109 import authorization

def run():
    config=c.read(c.TASK/'config.json');meta={r['id']:r for r in c.rows(c.PRIVATE/'data/pool_metadata.jsonl')}
    source=c.read(c.PRIVATE/'data/source_ids.json');neighbors=c.read(c.PRIVATE/'data/neighbors.json')
    ids=c.read(c.PRIVATE/'data/stage_a_ids.json');old=set(source)
    first={i:meta[i]['GT'] for i in ids}
    # Synthetic IN-MEMORY errors exercise the program, never stand in for9B.
    for label in c.LABELS[1:]:
        targets=[i for i in ids if meta[i]['GT']==label and i not in old][:40]
        assert len(targets)==40
        for i in targets:first[i]='Supported'
    hard=choose_hard(meta,first,config);request=supported_request(hard,neighbors,source,meta,config)
    second={i:'Supported' for i in request};manifest,summary=select(meta,first,second,neighbors,source,config)
    assert summary['N']==192 and summary['optimizer_updates']==24
    assert summary['role_counts']=={'hard_error':64,'protect_S':64,'retention':64}
    assert summary['hard_false_S']==64 and len({r['id'] for r in manifest})==192
    assert all(first[r['id']]!=r['GT'] for r in manifest if r['role']=='hard_error')
    assert all((first|second)[r['id']]==r['GT'] for r in manifest if r['role']!='hard_error')
    assert manifest==select(meta,dict(reversed(list(first.items()))),dict(reversed(list(second.items()))),neighbors,source,config)[0]
    altered={i:dict(m,paper_r1='Supported' if m.get('paper_r1')!='Supported' else 'Not Addressed',teacher_S_fraction=0.) for i,m in meta.items()}
    assert manifest==select(altered,first,second,neighbors,source,config)[0]
    stopped=[]
    def reject(name,call,kind=ValueError):
        try:call()
        except kind:stopped.append(name)
        else:raise AssertionError(name+' not rejected')
    reject('no_genuine_current_errors',lambda:choose_hard(meta,{i:meta[i]['GT'] for i in ids},config),InsufficientData)
    reject('no_current_correct_S',lambda:select(meta,first,{i:'Not Addressed' for i in request},neighbors,source,config),InsufficientData)
    rare=dict(first)
    for i in rare:
        if meta[i]['GT']=='Not Addressed':rare[i]=meta[i]['GT']
    reject('one_nonS_class_insufficient_no_recipe_change',lambda:choose_hard(meta,rare,config),InsufficientData)
    # Current-model provenance/prompt guard, with a tiny fabricated test ID only.
    dummy=dict(id='unit_fixture',sid='unit_patient',GT='Not Supported',role='train',eligible_109=True,prompt_token_sha256='unit_prompt')
    with TemporaryDirectory(prefix='109-test-') as temporary:
        path=Path(temporary)/'not_real_predictions.jsonl'
        row=dict(id=dummy['id'],sid=dummy['sid'],prediction_origin='actual_GPU_checkpoint',
            checkpoint_adapter_sha256='paper_R1_not_current',prompt_token_sha256='unit_prompt',parsed=dict(valid=True,verdict='Supported'))
        c.putl(path,[row]);reject('teacher_or_other_checkpoint',lambda:load_predictions(path,[dummy['id']],{dummy['id']:dummy}))
        row['checkpoint_adapter_sha256']=c.SOURCE_ADAPTER_SHA;row['prompt_token_sha256']='wrong';c.putl(path,[row])
        reject('wrong_actual_reference_prompt',lambda:load_predictions(path,[dummy['id']],{dummy['id']:dummy}))
    reject('CPU_stage_cannot_authorize_GPU',lambda:authorization(c.PRIVATE,Path('nonexistent'),execute=False),PermissionError)
    # Check the unchanged prompt constructor without loading a tokenizer/model.
    sys.path.insert(0,str(c.ROOT/'tasks/104_supervision_evidence'));from training104 import messages
    row=c.rows(c.PRIVATE/'data/pool.jsonl')[0]
    assert messages(row['claim'],row['reference'])==row['messages']
    assert 'GT' not in messages.__code__.co_varnames[:messages.__code__.co_argcount]
    assert not (set(meta)&{r['id'] for r in c.rows(c.PRIVATE/'data/baseline107.jsonl')})
    from analyze109 import point_rule,metrics
    rule=config['effect_rule'];old_metrics=dict(mcc=.5,percent_agreement=.8,false_S=12,
        per_class={g:dict(recall=.8) for g in c.LABELS})
    unsafe=dict(old_metrics,mcc=.52,false_S=10,per_class={g:dict(recall=.6 if g=='Not Addressed' else .8) for g in c.LABELS})
    assert point_rule(old_metrics,unsafe,'natural',1.,rule)['guard'] is False
    unchanged=point_rule(old_metrics,old_metrics,'natural',1.,rule);assert not unchanged['signal'] and unchanged['guard']
    # Regression on already saved107 labels, not a109 candidate/model call.
    baseline=c.rows(c.PRIVATE/'data/baseline107.jsonl')
    for panel,expected in [('natural',(.5032,319,12)),('pressure',(.3123,58,16))]:
        rows=[r for r in baseline if r['panel']==panel];value=metrics(rows,{r['id']:r['parsed']['verdict'] for r in rows})
        assert abs(value['mcc']-expected[0])<.0001 and (value['correct'],value['false_S'])==expected[1:]
    result=dict(task=109,CPU_only=True,synthetic_fixture_not9B_predictions=True,new_real_predictions=0,
        selector192_unique_counts_and_real_GT_mapping=True,deterministic_without_teacher_ranking=True,
        genuine_error_S_and_retention_guards=True,old_prompt_constructor_reused=True,
        train_eval_IDs_disjoint=True,NA_loss_cannot_hide_behind_falseS_gain=True,
        shared_evaluation_matches_saved107_reference=True,
        rejected_cases=stopped,model_imported=False,CUDA_initialized=False,clinical_effect_demonstrated=False)
    c.put(c.OUT/'cpu_checks.json',result);print(c.canonical(result))

if __name__=='__main__':run()
