"""Prepare only the original20 selection patients, author references and cached endpoints."""
from pathlib import Path
from collections import Counter
import json,sys,tarfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'));import common109 as c
sys.path.insert(0,str(ROOT/'tasks/104_supervision_evidence'));from training104 import messages
def main():
    private=ROOT/'.local_models/111_half_extension';out=ROOT/'outputs/111_half_extension';private.mkdir(exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    roles=c.read(ROOT/'outputs/103_lora_selection/patient_roles.json')['patients'];allowed=set(map(str,roles['selection']));forbidden=set(map(str,roles['train']+roles['confirmation']))
    assert len(allowed)==20 and not allowed&forbidden
    cohort=[r for r in c.rows(ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl') if str(r['sid']) in allowed]
    ids={r['id'] for r in cohort};assert len(ids)==len(cohort) and all(r['GT'] in c.LABELS for r in cohort)
    base107=c.rows(ROOT/'.local_models/109_boundary_replay/gpu_bundle/data/baseline107.jsonl');old500={r['id'] for r in base107};assert len(old500)==500 and old500<=ids
    remaining=ids-old500;raw={}
    with (ROOT/'.local_models/103_lora_selection/eligible.jsonl').open(encoding='utf-8-sig') as f:
        for line in f:
            row=json.loads(line)
            if row['id'] in ids:
                assert row['role']=='selection' and str(row['sid']) in allowed
                raw[row['id']]=row
    assert set(raw)==ids
    for r in cohort:assert r['GT']==raw[r['id']]['GT'] and str(r['sid'])==str(raw[r['id']]['sid'])
    # Only metadata is reused from108; never read bags/windows/tokens.
    meta108={r['id']:r for r in c.rows(ROOT/'.local_models/108_semantic_hierarchy/rows.jsonl') if str(r['sid']) in allowed}
    assert set(meta108)==ids and all(meta108[i]['GT']==raw[i]['GT'] for i in ids)
    data=[]
    for i in sorted(remaining):
        r=raw[i];data.append(dict(id=i,sid=str(r['sid']),claim=r['claim'],reference=r['reference'],reference_id=r['reference_id'],messages=messages(r['claim'],r['reference'])))
    c.putl(private/'inputs_new.jsonl',data)
    keys=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],author=r['author'],paper_r1=r['original'],subset='old500' if r['id'] in old500 else 'new',old_panel=next((x['panel'] for x in base107 if x['id']==r['id']),None),claim_sha256=c.digest(raw[r['id']]['claim']),reference_sha256=c.digest(raw[r['id']]['reference'])) for r in cohort]
    c.putl(private/'cohort_keys.jsonl',keys);c.putl(out/'cohort_metadata.jsonl',keys)
    sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'));from parse105 import parse
    old105={}
    for p in sorted((ROOT/'.local_models/105_brief_supervision/a800/evidence/results/eval/label_only').glob('batch-*.json')):
        for r in c.read(p)['records']:
            assert r['id'] not in old105;old105[r['id']]=dict(r,parsed=parse(r['content'],r['finish_reason']))
    assert set(old105)==old500
    for r in base107:assert r['prompt_token_sha256']==old105[r['id']]['prompt_token_sha256']
    half=c.rows(ROOT/'.local_models/110_update_interpolation/evidence/results/update_half/predictions.jsonl');quarter=c.rows(ROOT/'.local_models/110_update_interpolation/evidence/results/update_quarter/predictions.jsonl')
    assert {r['id'] for r in half}=={r['id'] for r in quarter}==old500
    for name,records in [('label_only105',list(old105.values())),('label_only107',base107),('update_half',half),('update_quarter',quarter)]:c.putl(private/(name+'_old500.jsonl'),records)
    history=[r for r in c.rows(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl') if r['local180']]
    assert len(history)==180 and {r['id'] for r in history}<=ids and Counter(r['panel'] for r in history)=={'natural':120,'pressure':60}
    assert all(r['GT']==raw[r['id']]['GT'] and r['predictions'].get('nine_lora') in c.LABELS for r in history)
    c.putl(private/'history103_180.jsonl',history)
    c.putl(out/'history103_ids.jsonl',[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],author=r['author'],panel=r['panel'],old500=r['id'] in old500) for r in history])
    asset=ROOT/'.local_models/105_brief_supervision/a800/backup/label_only/checkpoint_a';sha105=c.sha(asset/'adapter_model.safetensors')
    cfg=dict(task=111,arms=['label_only107','update_half','label_only105'],source_adapters={'label_only105':dict(path='/root/autodl-tmp/verifact111/adapters/label_only105',sha256=sha105),
        'label_only107':dict(path='/root/autodl-tmp/verifact109/bundle/source107/checkpoint_a',sha256=c.SOURCE_ADAPTER_SHA),
        'update_half':dict(path='/root/autodl-tmp/verifact110/results/adapters/update_half',sha256='f9c563951f7deb8b39da2f137db7ad51bda249f4d78a33931ecbba2d959adfdf')},
        new_IDs=len(remaining),full_IDs=len(ids),new_training=False,new_paid_API_CNY=0,hourly_CNY=1.58,task_GPU_cap_CNY=6,task_billing_start_beijing='2026-10-29 13:15:00',
        no_shutdown=True,no_release=True,initial_representative_cases='shortest, median, longest full prompt; each a formal first prediction',
        batching='same for all arms: representatives batch1; remaining <=12701 prompt tokens batch2, longer batch1; no truncation',
        decoding=dict(max_new_tokens=384,do_sample=False,num_beams=1,repetition_penalty=1.,thinking=False,parser='parse105'),
        historical103_arm='nine_lora',historical103_comparison='complete_recipe_comparison_not_single_component_ablation')
    c.put(ROOT/'tasks/111_half_extension/config.json',cfg);c.put(private/'config111.json',cfg)
    summary=dict(task=111,selection_patients=20,cohort_source='092 public valid atomic cohort restricted to original103 selection20',complete_cohort_N=len(ids),complete_GT=dict(Counter(r['GT'] for r in cohort)),
        old500_N=len(old500),new_N=len(remaining),new_GT=dict(Counter(raw[i]['GT'] for i in remaining)),author_full=dict(Counter(r['author'] for r in cohort)),
        no_duplicate_IDs=True,no_missing_author_reference=True,old500_subset_of_complete=True,old500_disjoint_new=True,confirmation_patients_used=False,
        history103_N=180,history103_old500_intersection=len({r['id'] for r in history}&old500),history103_new_intersection=len({r['id'] for r in history}&remaining),
        cached_reused_each_arm=500,existing_matching_new_receipts_found=0,full_reference_not_C48=True,GT_unchanged=True,full_cohort_natural_composition_must_not_equal_artificial_old500=True)
    c.put(out/'data_summary.json',summary)
    with tarfile.open(private/'inputs111.tar.gz','w:gz',compresslevel=1) as tar:
        for name in ['inputs_new.jsonl','cohort_keys.jsonl','config111.json']:tar.add(private/name,arcname=name,recursive=False)
    print(c.canonical(dict(**summary,input_archive_bytes=(private/'inputs111.tar.gz').stat().st_size)))
if __name__=='__main__':main()
