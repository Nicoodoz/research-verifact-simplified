"""Apply the frozen fixed MLP to new cached features, without fitting."""
from pathlib import Path
import argparse,json
import numpy as np
import torch
from fit_mlp117 import load_head,predict

def main():
 p=argparse.ArgumentParser();p.add_argument('--features',type=Path,nargs='+',required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 rows=[json.loads(l) for l in a.metadata.read_text(encoding='utf-8').splitlines() if l.strip()];rows=[r for r in rows if r['role']=='screen'];wanted={r['id'] for r in rows};assert len(rows)==len(wanted)
 features={}
 for folder in a.features:
  for path in (folder/'batches').glob('*.npz'):
   with np.load(path,allow_pickle=False) as z:
    for k,i in enumerate(z['ids'].astype(str)):
     if i in wanted:
      assert i not in features;features[i]=z['verdict_prefix'][k].copy()
 assert set(features)==wanted
 torch.set_num_threads(4);model,_=load_head(a.model);labels,probability=predict(model,torch.from_numpy(np.stack([features[r['id']] for r in rows])).float())
 from fit_probe117 import LABELS
 output=[dict(r,verdict=str(label),valid=True,probabilities=dict(zip(LABELS,probs.tolist())),probabilities_calibrated=False) for r,label,probs in zip(rows,labels,probability)]
 a.out.mkdir(parents=True,exist_ok=True);(a.out/'screen_predictions.jsonl').write_bytes(('\n'.join(json.dumps(r,ensure_ascii=False) for r in output)+'\n').encode())
 print(json.dumps(dict(N=len(rows),frozen=True)))
if __name__=='__main__':main()
