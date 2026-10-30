"""Reuse isolated copies of the unchanged117 CPU trainer on explicit new taps."""
from pathlib import Path
import argparse,importlib.util,json,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];PRIVATE=ROOT/'.local_models/126_conditional_state_readout'
sys.path.insert(0,str(ROOT/'tasks/117_verdict_probe'))
from fit_probe117 import metadata_rows,write_json

def load126(directory,rows):
    wanted={r['id'] for r in rows};found={};complete=json.loads((directory/'complete.json').read_text())
    protocol=json.loads((PRIVATE/'protocol.json').read_text(encoding='utf-8-sig'))
    if (complete['N']!=1914 or complete['suffix_ids']!=protocol['suffix_ids'] or not complete['same_forward_states']
        or complete['adapter_sha256']!=protocol['adapter_sha256'] or not complete['all_examples_same_suffix'] or complete['labels_in_inputs']):
        raise ValueError('Incomplete or different conditional126 extraction')
    for path in sorted((directory/'batches').glob('*.npz')):
        receipt=json.loads(path.with_suffix('.json').read_text())
        if (receipt['suffix_ids']!=protocol['suffix_ids'] or not receipt['prefix_saved_before_not']
            or receipt['adapter_sha256']!=protocol['adapter_sha256']):
            raise ValueError('The control state must precede the universal Not token')
        with np.load(path,allow_pickle=False) as z:
            ids=z['ids'].astype(str).tolist();a=z['verdict_prefix'];b=z['not_prefix']
            if a.shape!=(len(ids),4096) or b.shape!=a.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
                raise ValueError('Invalid conditional feature shard')
            if ids!=receipt['ids'] or set(ids)&set(found):raise ValueError('Duplicate or mismatched feature IDs')
            for i,k in enumerate(ids):found[k]=(a[i].copy(),b[i].copy())
    if set(found)!=wanted:raise ValueError('Only complete original1914 feature coverage is allowed')
    first=np.stack([found[r['id']][0] for r in rows]);last=np.stack([found[r['id']][1] for r in rows])
    return first,last

def isolated_trainer(name,feature,values):
    # A fresh module namespace keeps old117 CONFIG, functions and files untouched.
    spec=importlib.util.spec_from_file_location(name,ROOT/'tasks/117_verdict_probe/fit_mlp117.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    protocol=json.loads((PRIVATE/'protocol.json').read_text(encoding='utf-8-sig'))
    if any(module.CONFIG.get(k)!=v for k,v in protocol['MLP_config'].items()):
        raise ValueError('The original117 training/validation recipe changed')
    module.CONFIG=dict(module.CONFIG,feature=feature)
    module.feature_matrices=lambda _directory,_rows:({feature:values},dict(requested_N=len(_rows),dimensions={feature:values.shape[1]},source='same126causal_forward'))
    return module

def main():
    p=argparse.ArgumentParser();p.add_argument('--features',type=Path,required=True);a=p.parse_args()
    metadata=PRIVATE/'metadata.jsonl';rows=metadata_rows(metadata)
    if len(rows)!=1914 or sum(r['role']=='screen' for r in rows)!=160:raise ValueError('Freeze original1914 split')
    first,last=load126(a.features,rows)
    outputs={}
    for name,feature,x in [('prefix_control','verdict_prefix_same_forward',first),
                           ('conditional_state','concat_verdict_prefix_not_prefix',np.concatenate([first,last],axis=1))]:
        trainer=isolated_trainer('trainer126_'+name,feature,x);folder=PRIVATE/name
        result=trainer.fit_mlp(a.features,metadata,folder,threads=4)
        result.update(task=126,candidate=name,feature=feature,other1657_scored=False)
        selection=json.loads((folder/'selection.json').read_text(encoding='utf-8-sig'))
        selection.update(task=126,candidate=name,feature=feature,other1657_scored=False)
        write_json(folder/'selection.json',selection)
        write_json(folder/'fit_summary.json',result);outputs[name]=result
    write_json(PRIVATE/'result160.json',dict(task=126,heads=outputs,one_candidate_plus_same_forward_control=True,
        no_extra_GPU_extraction_for_control=True,other1657_scored=False))
    print(json.dumps({k:dict(selected_epoch=v['selected_epoch'],screen_metrics=v['screen_metrics']) for k,v in outputs.items()},ensure_ascii=False))

if __name__=='__main__':main()
