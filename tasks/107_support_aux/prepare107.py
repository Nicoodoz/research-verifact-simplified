"""Verify and copy the original196 and fixed selection500; never resample."""
from collections import Counter
import sys
import common107 as c

sys.path.insert(0, str(c.ROOT / 'tasks/105_brief_supervision'))
from data105 import construct_answer, training_plan, shared

TRAIN_SHA = '6abf6abb7949e5eca1e316f117c5269ccc87984452822920847cddb37e4008dc'
EVAL_SHA = 'c35ef6e408de00f5e860b84a65d079d768f52fdfb7af1b5d07923c14050174ce'

def support_target(label):
    if label not in c.LABELS:
        raise ValueError('Unknown original GT')
    return int(label == 'Supported')

def validate_training(rows, allowed, forbidden):
    if len(rows) != 196 or len({r['id'] for r in rows}) != 196:
        raise ValueError('Need exact196 unique training IDs')
    if Counter(r['GT'] for r in rows) != dict(zip(c.LABELS, (83, 62, 51))):
        raise ValueError('Wrong original class counts')
    if {str(r['sid']) for r in rows} - allowed or {str(r['sid']) for r in rows} & forbidden:
        raise ValueError('Training patient leakage')
    for row in rows:
        construct_answer(row)
        if set(shared.parse_answer(row)) != {'verdict'} or shared.parse_answer(row)['verdict'] != row['GT']:
            raise ValueError('Original label answer changed')

def main():
    old = c.read(c.ROOT / 'tasks/105_brief_supervision/config.json')
    config = dict(old, task=107, training_N=196, trainable_arms=list(c.ARMS))
    config['training'] = dict(old['training'], auxiliary=dict(type='linear_binary', weight=1.0,
        positive_label='Supported', representation='prompt_last', head_dtype='float32', head_seed=103028))
    config['evaluation'] = dict(old['evaluation'], arms=list(c.ARMS), old_predictions_reused=False,batch_size=2)
    config['execution_amendment'] = dict(user_authorized='2026-10-28 RTX5090 32GB handoff',
        GPU='NVIDIA GeForce RTX 5090',hourly_cny=2.88,billing_start_beijing='2026-10-28 20:40',
        evaluation_batch_policy='check2_then1_if_necessary_freeze_before_formal_evaluation',
        BF16_micro1_full_input_and_two_fresh_arm_design_unchanged=True)
    config['budget'] = dict(compute_hard_cap_cny=20, operating_line_cny=18,
        shutdown_unknown_reserve_cny=2, API_cap_cny=0, new_disk_allowed=False)
    config['design'] = dict(sole_change='training_only_S_nonS_auxiliary_BCE', fresh_base_both_arms=True,
        initialization='identical_original_base_and_LoRA_seed103027', auxiliary_weight_fixed=1,
        inference_auxiliary_used=False, main_loss_unchanged=True, confirmation40_used=False,
        main_comparison='new_two_arm_common_valid_IDs_separate_natural_pressure')
    c.put(c.TASK / 'config.json', config)
    rolepath = c.ROOT / 'outputs/103_lora_selection/patient_roles.json'
    roles = c.read(rolepath)['patients']
    train, selection, confirmation = (set(map(str, roles[k])) for k in ('train', 'selection', 'confirmation'))
    if train & selection or train & confirmation or selection & confirmation:
        raise ValueError('Frozen patient roles overlap')
    source = c.ROOT / '.local_models/105_brief_supervision/train/label_only.jsonl'
    original = c.ROOT / '.local_models/104_supervision_evidence/paired/label_only.jsonl'
    evaluation = c.ROOT / '.local_models/105_brief_supervision/eval_inputs.jsonl'
    if c.sha(source) != TRAIN_SHA or c.sha(original) != TRAIN_SHA or c.sha(evaluation) != EVAL_SHA:
        raise ValueError('Original104/105 input bytes changed')
    rows = c.rows(source)
    validate_training(rows, train, selection | confirmation)
    # Read only the already allowed train40+selection20 source. Never access confirmation content.
    source_rows = {r['id']: r for r in c.rows(c.ROOT / '.local_models/103_lora_selection/eligible.jsonl')}
    if {str(r['sid']) for r in source_rows.values()} & confirmation:
        raise ValueError('Unexpected confirmation data in allowed historical source')
    for row in rows:
        original_row = source_rows[row['id']]
        if any(row[k] != original_row[k] for k in ('GT', 'claim', 'reference', 'sid')):
            raise ValueError('Original physician GT/reference/claim changed')
    erows = c.rows(evaluation)
    keys = c.rows(c.ROOT / 'outputs/105_brief_supervision/eval_keys.jsonl')
    if len(erows) != 500 or len({r['id'] for r in erows}) != 500 or [r['id'] for r in keys] != [r['id'] for r in erows]:
        raise ValueError('Fixed selection500 identity/order changed')
    if {str(r['sid']) for r in erows} - selection or {r['id'] for r in rows} & {r['id'] for r in erows}:
        raise ValueError('Train/evaluation leakage')
    if any('GT' in r or 'answer' in r for r in erows):
        raise ValueError('Evaluation inference input contains labels')
    for arm in c.ARMS:
        c.frozen(c.PRIVATE / 'train' / (arm + '.jsonl'), source.read_bytes())
    c.frozen(c.PRIVATE / 'eval_inputs.jsonl', evaluation.read_bytes())
    for name in ('eval_keys.jsonl', 'eval_manifest.jsonl', 'train_manifest.jsonl', 'training_plan.json'):
        c.frozen(c.OUT / name, (c.ROOT / 'outputs/105_brief_supervision' / name).read_bytes())
    targets = [dict(id=r['id'], sid=r['sid'], GT=r['GT'], support_target=support_target(r['GT'])) for r in rows]
    c.putl(c.OUT / 'auxiliary_targets.jsonl', targets)
    plan = training_plan([r['id'] for r in rows])
    assert len(plan) == 50 and plan[-1]['consumed'] == 392 and [s['loss_divisor'] for s in plan if s['epoch_end']] == [4, 4]
    c.put(c.OUT / 'data_checks.json', dict(status='PASS', train_N=196, train_patients=len({r['sid'] for r in rows}),
        classes=dict(Counter(r['GT'] for r in rows)), auxiliary_classes=dict(Counter(str(r['support_target']) for r in targets)),
        evaluation={p:dict(N=sum(r['panel']==p for r in keys), GT=dict(Counter(r['GT'] for r in keys if r['panel']==p))) for p in ('natural','pressure')},
        selection_patients=len({r['sid'] for r in erows}), train_selection_patient_overlap=0,
        training_sha256=TRAIN_SHA, eval_inputs_sha256=EVAL_SHA, patient_roles_sha256=c.sha(rolepath),
        both_train_files_byte_identical=True, original_claim_GT_reference_unchanged=True,
        optimizer_steps_each=50, consumed_each=392, epoch_tail_divisors=[4,4],
        confirmation_content_read=False, all100_historically_exposed=True, new_holdout=False,
        GPU_started=False, API_calls=0))
    c.put(c.OUT / 'patient_roles107.json', dict(train=sorted(train), selection=sorted(selection),
        confirmation_content_labels_predictions_not_used=True, all100_historically_exposed=True, source_sha256=c.sha(rolepath)))
    print(c.canonical(c.read(c.OUT / 'data_checks.json')))

if __name__ == '__main__':
    main()
