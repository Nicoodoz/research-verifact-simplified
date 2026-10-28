"""Select authorized patients and existing original CLS features; no cache rebuild/hash scan."""
from collections import Counter
import sys
import numpy as np
import common108 as c

def main():
    roles=c.read(c.ROOT/'outputs/103_lora_selection/patient_roles.json')['patients']
    train_patients=set(map(str,roles['train']));selection_patients=set(map(str,roles['selection']))
    assert len(train_patients)==40 and len(selection_patients)==20 and not train_patients&selection_patients
    ordered=sorted(train_patients,key=lambda sid:c.digest('108/internal-patient-split/92027/'+sid))
    val_patients=set(ordered[:8]);gradient_patients=train_patients-val_patients
    keys=c.rows(c.ROOT/'outputs/105_brief_supervision/eval_keys.jsonl');keymap={r['id']:r for r in keys}
    original=c.rows(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')
    allowed=[r for r in original if str(r['sid']) in train_patients|selection_patients]
    metadata=[]
    for r in allowed:
        panel=keymap[r['id']]['panel'] if r['id'] in keymap else ('selection_remaining' if str(r['sid']) in selection_patients else 'training')
        if r['id'] in keymap:assert r['GT']==keymap[r['id']]['GT'] and str(r['sid'])==str(keymap[r['id']]['sid'])
        metadata.append(dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],author=r['author'],panel=panel,
            paper_r1=r.get('original'),historical_role=r.get('historical_role')))
    by={r['id']:r for r in metadata};assert set(keymap)<=set(by)
    split=dict(train=[r['id'] for r in metadata if r['sid'] in gradient_patients],
        validation=[r['id'] for r in metadata if r['sid'] in val_patients],selection=[r['id'] for r in keys])
    for part in split.values():assert len(part)==len(set(part))
    assert not set(split['train'])&set(split['validation']) and not (set(split['train'])|set(split['validation']))&set(split['selection'])
    bags_all={r['id']:r for r in c.rows(c.ROOT/'outputs/092_task_adapted_verifier/bags.jsonl')}
    bags=[bags_all[r['id']] for r in metadata];assert all(r['windows'] for r in bags)
    feature=c.ROOT/'.local_models/092/activations/cls24.npy';array=np.load(feature,mmap_mode='r')
    assert array.ndim==2 and array.shape[1]==1024 and array.dtype==np.float32
    assert max(i for r in bags for i in r['windows'])<len(array)
    c.putl(c.PRIVATE/'rows.jsonl',metadata);c.putl(c.PRIVATE/'bags.jsonl',bags);c.put(c.PRIVATE/'split.json',split)
    data=dict(feature_path=str(feature.resolve()),bags_path=str(c.PRIVATE/'bags.jsonl'),rows_path=str(c.PRIVATE/'rows.jsonl'),
        split_path=str(c.PRIVATE/'split.json'),settings=dict(seed=92027,epochs=5,head_lr=.001,weight_decay=.01,dropout=.1,batch_size=8,clip=1.))
    c.put(c.PRIVATE/'data.json',data)
    summary=dict(task=108,original_pretrained_cls24_reused=True,supervised092_checkpoint_used=False,
        feature_shape=list(array.shape),feature_bytes=array.nbytes,no_large_cache_hash_or_copy=True,
        training_authorized_patients=40,gradient_patients=sorted(gradient_patients),validation_patients=sorted(val_patients),
        selection_patients=20,all100_historically_exposed=True,confirmation40_used_for_selection=False,
        panels={part:dict(N=len(ids),GT=dict(Counter(by[i]['GT'] for i in ids)),patients=len({by[i]['sid'] for i in ids}),windows=sum(len(bags_all[i]['windows']) for i in ids)) for part,ids in split.items()},
        selection_panel_counts=dict(Counter(keymap[i]['panel'] for i in split['selection'])),
        max_windows=max(len(bags_all[i]['windows']) for part in split.values() for i in part),
        remaining_selection_metadata_N=sum(r['panel']=='selection_remaining' for r in metadata),
        selection500_not_used_for_epoch_choice=True,GT_and_C48_unchanged=True,all_windows_retained=True)
    c.put(c.OUT/'data_summary.json',summary);print(c.canonical(summary))

if __name__=='__main__':main()
