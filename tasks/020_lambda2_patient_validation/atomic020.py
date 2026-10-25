"""020 ledger durability without Windows rename-over-open semantics."""
import json, os
from pathlib import Path

def _decode(path):
    try:
        v=json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return v if isinstance(v,dict) else None
    except (OSError,ValueError,TypeError):
        return None

def load(path):
    path=Path(path); shadow=path.with_name(path.stem+'_shadow'+path.suffix)
    values=[v for v in (_decode(path),_decode(shadow)) if v is not None]
    if not values: raise ValueError('No valid ledger copy')
    return max(values,key=lambda v:int(v.get('_checkpoint_seq',0)))

def save(path,value):
    path=Path(path); shadow=path.with_name(path.stem+'_shadow'+path.suffix)
    encoded=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n'
    for target in (shadow,path):
        with target.open('w',encoding='utf-8',newline='\n') as f:
            f.write(encoded);f.flush();os.fsync(f.fileno())
