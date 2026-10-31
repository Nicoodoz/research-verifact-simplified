"""CPU checks for the budget regression, input contract and frozen139 package."""
from pathlib import Path
import ast, json, sys
from budget139 import deadlines
from prompt139 import messages, original_messages, assert_unchanged_rope
R=Path(__file__).resolve().parents[2];P=R/'.local_models/139_full_repeat'


def main():
    session=dict(start_epoch=0,GPU_cap_CNY=20,hourly_CNY=1)
    job=dict(compute_limit_seconds=2700,save_reserve_seconds=900)
    full=deadlines(1000,session,job)
    assert full['compute_end']==3700 and full['stage_end']==4600
    short=deadlines(71000,session,job)
    assert short['compute_end']==71100 and short['stage_end']==72000
    row=dict(claim='He said "no".\nDose2mg',reference='α\\β\n{}')
    base=original_messages(row['claim'],row['reference']);new=messages(row)
    assert new[0]==base[0] and new[1]['content']==base[1]['content']+'\n\n'+base[1]['content']
    assert new==messages(dict(row,GT='Not Addressed',verdict='Supported'))
    config=dict(max_position_embeddings=262144,rope_parameters={'rope_type':'default','rope_theta':10000000})
    assert_unchanged_rope(config,dict(config),32768)
    capacity_only=assert_unchanged_rope(config,dict(config,max_position_embeddings=32768),32768)
    assert capacity_only['allocation_metadata_only_change'] is True
    try:assert_unchanged_rope(config,dict(config,rope_scaling={'factor':2}),32768)
    except RuntimeError:pass
    else:raise AssertionError('Changed RoPE accepted')
    for f in (R/'tasks/139_full_repeat').glob('*.py'):
        assert not f.read_bytes().startswith(b'\xef\xbb\xbf');ast.parse(f.read_text(encoding='utf-8'))
    data=json.loads((P/'screen160/job.json').read_text());expected=json.loads((P/'source/screen160_ids.json').read_text())
    assert len(data['ids'])==160 and set(data['ids'])==set(expected)
    assert data['first_formal_ID']=='6cc9f4bd-2c62-8e18-3405-ec5fdd381657'
    assert data['compute_limit_seconds']==2700 and data['total_stage_limit_seconds']==3600
    for f in (P/'screen160/bundle').rglob('*.py'):ast.parse(f.read_text(encoding='utf-8'))
    assert 'torch' not in sys.modules and 'transformers' not in sys.modules
    from analyze139 import compare
    labels=('Supported','Not Supported','Not Addressed')
    keys=[dict(id=str(i),sid=str(i),GT=g,paper_r1=g) for i,g in enumerate(labels)]
    reference={r['id']:r['GT'] for r in keys};candidate=dict(reference);candidate['1']='Supported'
    comparison=compare(keys,reference,candidate,'full_pool120')
    assert comparison['delta_correct']==-1 and comparison['delta_false_S']==1
    assert set(comparison['scores'])=={'full_pool120','full_repeat','paper_r1'}
    result=dict(task=139,status='PASS',budget_regression='2700 computation plus900 save',same160=True,
        full_user_repeated=True,GT_not_input=True,source_inputs_not_retokenized=True,
        standard_metric_label_routing_checked=True,capacity_metadata_only_change_allowed=True,no_GPU=True)
    out=R/'outputs/139_full_repeat/cpu_selfcheck.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'));print(json.dumps(result))


if __name__=='__main__':main()
