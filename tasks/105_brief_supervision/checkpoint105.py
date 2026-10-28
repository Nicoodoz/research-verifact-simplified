"""Two rolling slots; pointer commits only complete adapter/optimizer/RNG state."""
from pathlib import Path
import random
import numpy as np
import torch
import common105 as c

def save(model,optimizer,scheduler,work,step,consumed,fingerprint):
    work=Path(work);work.mkdir(parents=True,exist_ok=True)
    pointer=work/'resume.json'
    old=c.read(pointer) if pointer.exists() else None
    slot='checkpoint_b' if old and old['slot']=='checkpoint_a' else 'checkpoint_a'
    folder=work/slot;folder.mkdir(exist_ok=True)
    model.save_pretrained(folder,safe_serialization=True)
    state=dict(optimizer=optimizer.state_dict(),scheduler=scheduler.state_dict(),step=step,consumed=consumed,
               torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [],
               python_rng=random.getstate(),numpy_rng=np.random.get_state(),fingerprint=fingerprint)
    temp=folder/'training_state.pt.tmp';torch.save(state,temp);temp.replace(folder/'training_state.pt')
    files={p.name:c.sha(p) for p in folder.iterdir() if p.is_file() and p.name!='checkpoint_complete.json' and not p.name.endswith('.tmp')}
    complete=dict(step=step,consumed=consumed,fingerprint=fingerprint,files=files)
    c.put(folder/'checkpoint_complete.json',complete)
    c.put(pointer,dict(slot=slot,step=step,consumed=consumed,complete_sha256=c.sha(folder/'checkpoint_complete.json'),fingerprint=fingerprint))
    return folder

def load(optimizer,scheduler,work,fingerprint,restore_adapter):
    work=Path(work);pointer=c.read(work/'resume.json')
    if pointer['fingerprint']!=fingerprint:raise ValueError('Resume configuration/data/code fingerprint mismatch')
    if pointer['slot'] not in {'checkpoint_a','checkpoint_b'}:raise ValueError('Unexpected checkpoint path')
    folder=work/pointer['slot']
    assert c.sha(folder/'checkpoint_complete.json')==pointer['complete_sha256']
    complete=c.read(folder/'checkpoint_complete.json')
    assert complete['fingerprint']==fingerprint
    for name,sha in complete['files'].items():assert Path(name).name==name and c.sha(folder/name)==sha
    state=torch.load(folder/'training_state.pt',map_location='cpu',weights_only=False)
    assert state['step']==pointer['step'] and state['consumed']==pointer['consumed'] and state['fingerprint']==fingerprint
    restore_adapter(folder)
    optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
    torch.set_rng_state(state['torch_rng']);random.setstate(state['python_rng']);np.random.set_state(state['numpy_rng'])
    if state['cuda_rng']:torch.cuda.set_rng_state_all(state['cuda_rng'])
    return pointer['step'],pointer['consumed'],folder

