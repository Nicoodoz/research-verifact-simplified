"""Match original117 MLP selection on claim-only features; CPU entry only."""
from __future__ import annotations

import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/123_claim_only_control'
sys.path.insert(0, str(ROOT / 'tasks/117_verdict_probe'))
from fit_mlp117 import CONFIG, fit_mlp
from fit_probe117 import metadata_rows, write_json
from fit123 import checked_features


def prepare_metadata(private):
    def read_rows(path):
        return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    original = metadata_rows(ROOT / '.local_models/117_verdict_probe/metadata.jsonl')
    full = read_rows(private / 'metadata.jsonl')
    by_id = {r['id']:r for r in full}
    training = [r for r in original if r['role'] in ('train','validation')]
    screens = [r for r in full if r['role']=='screen']
    if Counter(r['role'] for r in training) != {'train':1024,'validation':730} or len(screens)!=1817:
        raise ValueError('Expected original1024/730 split and all1817 development IDs')
    for row in original:
        other=by_id[row['id']]
        if row['GT']!=other['GT'] or str(row['sid'])!=str(other['sid']):
            raise ValueError('Original training/validation/oldscreen labels or patients changed')
    path = private / 'metadata_original_mlp.jsonl'
    rows = training+screens
    path.write_bytes(('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n').encode('utf-8'))
    checked = metadata_rows(path)
    patient_n={role:len({str(r['sid']) for r in checked if r['role']==role}) for role in ('train','validation','screen')}
    if patient_n != {'train':32,'validation':8,'screen':20}:
        raise ValueError('Original32/8/20 isolation changed')
    source=json.loads((ROOT/'.local_models/117_verdict_probe/mlp_initial/selection.json').read_text(encoding='utf-8-sig'))
    if any(source['config'].get(k)!=v for k,v in CONFIG.items()) or CONFIG.get('class_weight'):
        raise ValueError('Original unweighted MLP recipe changed')
    protocol=dict(candidate='claim_only_original_mlp',train_N=1024,validation_N=730,screen_N=1817,
        patients=patient_n,training_order_identical_to_original=True,config=dict(CONFIG),
        epoch_selection='original validation MCC, then PA, then fewer falseS; earliest tie',
        original_reference_selected_epoch=source['selected_epoch'],fixed_epoch_for_claim_only=False,
        max_epochs=40,early_stopping_patience=8,seed=117,extra_GPU_extraction=False,
        features='Same new5492 claim-only frozen107 extraction as fixed10 fullsqrt control',
        screen_used_for_selection=False,confirmation40_used=False,status='PREPARED_NOT_FIT')
    write_json(private/'original_mlp_control_protocol.json',protocol)
    return path,full,protocol


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features',type=Path)
    parser.add_argument('--private',type=Path,default=PRIVATE)
    parser.add_argument('--out',type=Path,default=PRIVATE/'fit_original_mlp')
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args()
    metadata,full,protocol=prepare_metadata(args.private)
    if args.prepare_only:
        print(json.dumps(protocol,ensure_ascii=False));return
    if args.features is None:
        parser.error('--features is required after the claim-only extraction is complete')
    # Reject accidental reuse of the full-reference cache before original fitting.
    values,_=checked_features(args.features,full,args.private)
    del values;gc.collect()
    result=fit_mlp(args.features,metadata,args.out,threads=4)
    write_json(args.out/'matched_control_protocol.json',dict(protocol,status='COMPLETE'))
    print(json.dumps(dict(selected_epoch=result['selected_epoch'],completed_epochs=result['completed_epochs'],
                         screen_metrics=result['screen_metrics']),ensure_ascii=False))


if __name__=='__main__':
    main()
