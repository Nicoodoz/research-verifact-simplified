"""Apply an already frozen linear head to additional cached features, no fitting."""
from pathlib import Path
import argparse,sys,json
import numpy as np
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).parent))
from fit_probe117 import predict_head,write_json,metrics

def main():
 p=argparse.ArgumentParser();p.add_argument('--features',type=Path,nargs='+',required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--head-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 rows=[json.loads(l) for l in a.metadata.read_text(encoding='utf-8').splitlines() if l.strip()];rows=[r for r in rows if r['role']=='screen'];wanted={r['id'] for r in rows};assert len(rows)==len(wanted)
 found={m:{} for m in ['verdict_prefix','prompt_end']}
 for folder in a.features:
  for path in sorted((folder/'batches').glob('*.npz')):
   with np.load(path,allow_pickle=False) as z:
    for k,i in enumerate(z['ids'].astype(str)):
     if i not in wanted:continue
     assert i not in found['verdict_prefix'],'Duplicate extraction would change first-pass provenance'
     for m in found:found[m][i]=z[m][k].copy()
 assert set(found['verdict_prefix'])==wanted,'Additional predictions require every intended feature'
 a.out.mkdir(parents=True,exist_ok=True)
 for m,features in found.items():
  with np.load(a.head_dir/(m+'_head.npz'),allow_pickle=False) as head:
   labels,probabilities=predict_head(head,np.stack([features[r['id']] for r in rows]));classes=head['classes'].astype(str).tolist()
  output=[dict(r,verdict=str(label),valid=True,probabilities=dict(zip(classes,probs.tolist())),probabilities_calibrated=False) for r,label,probs in zip(rows,labels,probabilities)]
  (a.out/(m+'_screen_predictions.jsonl')).write_bytes(('\n'.join(json.dumps(r,ensure_ascii=False) for r in output)+'\n').encode())
  write_json(a.out/(m+'_screen_metrics.json'),metrics(rows,labels))
 write_json(a.out/'frozen_head_source.json',dict(source=str(a.head_dir),N=len(rows),refit=False))
 print(json.dumps(dict(N=len(rows),frozen=True)))
if __name__=='__main__':main()
