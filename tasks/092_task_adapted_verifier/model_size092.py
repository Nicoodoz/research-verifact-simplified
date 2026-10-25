import math
from safetensors import safe_open
import common092 as c
path=c.ROOT/'.local_models/032/deberta_v3_nli/model.safetensors'
with safe_open(path,framework='np') as f:counts={k:math.prod(f.get_slice(k).get_shape()) for k in f.keys()}
total=sum(counts.values());backbone=sum(v for k,v in counts.items() if k.startswith('deberta.'))
top=sum(v for k,v in counts.items() if k.startswith('deberta.encoder.layer.23.'))
c.put(c.OUT/'model_size.json',dict(pretrained_checkpoint_parameters=total,backbone_parameters=backbone,pretrained_top_block_parameters=top,aggregation_classifier_parameters=6148,independent_verifier_parameters=backbone+6148,finetuned_trainable_parameters=top+6148,frozen_trainable_parameters=6148,pretrained_checkpoint_bytes=path.stat().st_size,model_revision='b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7',full_checkpoint_not_published=True))
print(c.read(c.OUT/'model_size.json'))
