"""Aggregate actual mining and the fixed selection, without publishing cases."""
from collections import Counter
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'))
import common109 as c
from select109 import load_predictions
b=ROOT/'.local_models/109_boundary_replay/gpu_bundle';w=ROOT/'.local_models/109_boundary_replay/gpu_evidence/results'
meta={r['id']:r for r in c.rows(b/'data/pool_metadata.jsonl')};request=c.read(w/'supported_request.json')
a=load_predictions(w/'mining_a/predictions.jsonl',c.read(b/'data/stage_a_ids.json'),meta)
s=load_predictions(w/'mining_s/predictions.jsonl',request['ids'],meta);p=a|s
selected=c.rows(w/'selected_manifest.jsonl');baseline=c.rows(b/'data/baseline107.jsonl')
train_patients={str(r['sid']) for r in selected};evaluation_patients={str(r['sid']) for r in baseline}
assert len(selected)==len({r['id'] for r in selected})==192
assert not train_patients&evaluation_patients
assert all(r['GT']==meta[r['id']]['GT'] and str(r['sid'])==str(meta[r['id']]['sid']) and meta[r['id']]['eligible_109'] and meta[r['id']]['role']=='train' for r in selected)
assert all(p[r['id']]!=r['GT'] and p[r['id']] is not None if r['role']=='hard_error' else p[r['id']]==r['GT'] for r in selected)
result=dict(task=109,source='actual107_label_only_GPU_first_receipts',source_adapter_sha256=c.SOURCE_ADAPTER_SHA,
    mining_N=len(p),stage_a_N=len(a),stage_s_N=len(s),invalid=sum(v is None for v in p.values()),
    stage_a_GT=dict(Counter(meta[i]['GT'] for i in a)),
    stage_a_errors_by_GT=dict(Counter(meta[i]['GT'] for i,v in a.items() if v is not None and v!=meta[i]['GT'])),
    stage_a_false_S_by_GT=dict(Counter(meta[i]['GT'] for i,v in a.items() if v=='Supported')),
    S_current_correct=sum(v=='Supported' for v in s.values()),selection=c.read(w/'selection_summary.json'),
    training_patients=len(train_patients),evaluation_patients=len(evaluation_patients),patient_overlap=0,
    training_GT_unchanged=True,source107_retained_N=sum(r['source107'] for r in selected),
    hard_semantic104_status=dict(Counter(meta[r['id']]['semantic104_status'] for r in selected if r['role']=='hard_error')),
    training_input_tokens=sum(r['input_tokens'] for r in selected),training_max_input_tokens=max(r['input_tokens'] for r in selected),
    clinical_relationship_pairs_certified=False,selection500_not_used_for_sampling=True,
    classification_gain_established_by_mining=False)
c.put(ROOT/'outputs/109_boundary_replay/mining_summary.json',result)
print(c.canonical(result))
