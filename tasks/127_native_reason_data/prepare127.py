"""Keep all original40-patient data; pair only externally reviewed reasons."""
from collections import Counter
from pathlib import Path
import argparse,json
from data_contract127 import ROOT,VERSION,LABELS,build_record,reason_issues,reason_state,assert_pair

PRIVATE=ROOT/'.local_models/127_native_reason_data'

def rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]

def put_rows(path,values):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='\n') as f:
        for value in values:f.write(json.dumps(value,ensure_ascii=False,separators=(',',':'))+'\n')

def load_pool():
    # This split file contains only the original32/8 training-side patient IDs.
    split=json.loads((ROOT/'.local_models/116_research_cycle/data_split.json').read_text(encoding='utf-8-sig'))
    train=set(map(str,split['gradient_patients']));validation=set(map(str,split['internal_validation_patients']))
    if len(train)!=32 or len(validation)!=8 or train&validation:raise ValueError('Fixed32/8 patient split changed')
    pool=rows(ROOT/'.local_models/106_label_preparation/training_pool.jsonl')
    if len({r['id'] for r in pool})!=len(pool):raise ValueError('Duplicate original training-pool ID')
    if {str(r['sid']) for r in pool}!=train|validation:raise ValueError('Only original40 training patients allowed')
    return pool,{str(s):'train' for s in train}|{str(s):'validation' for s in validation}

def ledger_and_counts(all_labels,paired_reasons,out):
    paired_ids={x['id'] for x in paired_reasons}
    ledger=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],fit_role=r['fit_role'],
        reason_state=reason_state(r.get('reason_metadata'),r['issue_codes']),issue_codes=r['issue_codes'],
        teacher_disagreement=r['teacher_disagreement'],retained_label_only=True,
        paired=r['id'] in paired_ids) for r in all_labels]
    put_rows(out/'issue_ledger.jsonl',ledger)
    def by_role_gt(values):
        return {role:{g:sum(r['fit_role']==role and r['GT']==g for r in values) for g in LABELS}
                for role in ('train','validation')}
    return dict(original_GT_counts={g:sum(r['GT']==g for r in all_labels) for g in LABELS},
        original_by_role_GT=by_role_gt(all_labels),paired_by_role_GT=by_role_gt(paired_reasons),
        reason_state_counts=dict(Counter(r['reason_state'] for r in ledger)),
        unreviewed_are_pending_not_semantically_excluded=True)

def prepare(annotations_path,out):
    pool,roles=load_pool();by_id={r['id']:r for r in pool}
    annotations={} if annotations_path is None else {r['id']:r for r in rows(annotations_path)}
    if annotations_path and len(annotations)!=len(rows(annotations_path)):raise ValueError('Duplicate reason annotation ID')
    if not set(annotations)<=set(by_id):raise ValueError('Annotation outside original40-patient training pool')
    if (out/'manifest.json').exists():raise FileExistsError('Use a new output directory; preserve prior preparation')
    all_labels=[];paired_labels=[];paired_reasons=[];issues=Counter()
    for row in pool:
        annotation=annotations.get(row['id']);role=roles[str(row['sid'])]
        label=build_record(row,role,'label_only',annotation)
        assert label['claim'].encode('utf-8')==row['claim'].encode('utf-8')
        assert label['reference'].encode('utf-8')==row['reference'].encode('utf-8')
        all_labels.append(label);issues.update(label['issue_codes'])
        if not reason_issues(row,annotation):
            reason=build_record(row,role,'verdict_reason',annotation);assert_pair(label,reason)
            paired_labels.append(label);paired_reasons.append(reason)
    put_rows(out/'all_label_only.jsonl',all_labels)
    for role in ('train','validation'):
        put_rows(out/'paired'/(role+'_label_only.jsonl'),[r for r in paired_labels if r['fit_role']==role])
        put_rows(out/'paired'/(role+'_verdict_reason.jsonl'),[r for r in paired_reasons if r['fit_role']==role])
    manifest=dict(contract_version=VERSION,original_pool_N=len(pool),all_label_only_N=len(all_labels),
        original_patients=40,role_counts=dict(Counter(r['fit_role'] for r in all_labels)),
        reliable_paired_N=len(paired_reasons),paired_role_counts=dict(Counter(r['fit_role'] for r in paired_reasons)),
        retained_unpaired_N=len(all_labels)-len(paired_reasons),issue_counts=dict(issues),
        reason_source='Current Codex/sub-agent AI-assisted drafts after full-reference review; this script never generates reasons or certifies medical truth',
        same_IDs_and_order_in_two_paired_arms=True,original_GT_and_clinical_UTF8_values_preserved=True,
        prompt='104 task/definitions unchanged; independent127 output rule: required verdict, optional1--3 sentence reason',
        loss='Reuse loss105.backbone_loss and segmented_hidden_loss unchanged; no new weights',
        selection20_read=False,confirmation40_read=False,new_GPU_calls=0,new_API_calls=0,
        ready_for_effect_experiment=False)
    manifest.update(ledger_and_counts(all_labels,paired_reasons,out))
    (out/'manifest.json').write_bytes((json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(manifest,ensure_ascii=False))
    return manifest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--annotations',type=Path);p.add_argument('--out',type=Path,default=PRIVATE/'contract_initial')
    a=p.parse_args();prepare(a.annotations,a.out)
