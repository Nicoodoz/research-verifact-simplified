"""Additional execution checks, not an independent scientific audit."""
import sys, json, hashlib
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tasks/032_evidence_relation_correction'))
import common032 as c
import learning032 as l
import torch

def main():
    c.block_network()
    out = c.OUT / 'verification_supplementary_001'
    c.require(not out.exists(), 'Do not overwrite verification')
    rows, data = l.load_arrays()
    checks = {}
    def check(name, value):
        checks[name] = bool(value)
        c.require(bool(value), name)
    prep = c.read(c.OUT / 'preparation_001/manifest.json')
    for rel, sha in prep['sources'].items():
        check('source:' + rel, c.sha(ROOT / 'outputs' / rel) == sha)
    for name, sha in prep['files'].items():
        check('preparation:' + name, c.sha(c.OUT / 'preparation_001' / name) == sha)
    check('n_claims', len(rows) == 3675)
    train = {r['proposition_id']: i for i, r in enumerate(rows) if r['split'] == 'train'}
    confirm = {r['proposition_id']: i for i, r in enumerate(rows) if r['split'] == 'confirmation'}
    labels = c.lines(c.OUT / 'preparation_001/training_labels.jsonl')
    check('training_label_ids', {r['proposition_id'] for r in labels} == set(train))
    check('blind_has_no_GT', all('human_gt' not in r and 'GT' not in r for r in rows))
    check('patient_isolation', not {rows[i]['subject_id'] for i in train.values()} & {rows[i]['subject_id'] for i in confirm.values()})
    folds = c.read(c.OUT / 'preparation_001/folds.json')
    valid = [sid for f in folds for sid in f['validation_patients']]
    check('four_fold_coverage', len(valid) == len(set(valid)) == 28)
    for fold in folds:
        check('fold:' + str(fold['fold']), not set(fold['training_patients']) & set(fold['validation_patients']))
    mapping = c.lines(c.OUT / 'nli_001/bags.jsonl')
    cache = np.load(c.CACHE / 'pair_cache/features.npy', mmap_mode='r')
    done = np.load(c.CACHE / 'pair_cache/done.npy', mmap_mode='r')
    check('all_NLI_complete', np.all(done == 1))
    check('NLI_finite', np.isfinite(cache).all())
    check('NLI_prob_sums', np.allclose(cache[:, :3].sum(1), 1, atol=2e-6))
    check('NLI_logs_match', np.allclose(cache[:, 3:6], np.log(np.maximum(cache[:, :3], 1e-7)), atol=2e-6))
    check('projection_norms', np.allclose(np.linalg.norm(cache[:, 6:38], axis=1), 1, atol=2e-5))
    nm = c.read(c.OUT / 'nli_001/manifest.json')
    check('bags_hash', c.sha(c.CACHE / 'bags.npz') == nm['bags_sha256'])
    check('bag_mapping_hash', c.sha(c.OUT / 'nli_001/bags.jsonl') == nm['bag_mapping_sha256'])
    check('all_bags_nonempty', data['mask'].any(1).all())
    for i, bag in enumerate(mapping):
        check('bag_id:' + str(i), bag['proposition_id'] == rows[i]['proposition_id'])
        for j, member in enumerate(bag['members']):
            check('bag_values:' + str(i) + ':' + str(j), np.array_equal(data['x'][i, j, :38], cache[member['pair']]))
    frozen = c.read(c.OUT / 'training_001/freeze.json')
    for name, sha in frozen['code'].items():
        check('training_code:' + name, c.sha(c.TASK / name) == sha)
    check('training_input_hash', c.sha(c.OUT / 'preparation_001/inputs_blind.jsonl') == frozen['input_sha256'])
    models = []
    for folder in [c.OUT / 'training_001/models', c.OUT / 'inference_001/models']:
        for p in sorted(folder.rglob('model.json')):
            meta = c.read(p)
            check('training_IDs:' + str(p), set(meta['training_ids']) <= set(train))
            check('weights:' + str(p), c.sha(p.parent / 'weights.pt') == meta['weights_sha256'])
            ii = np.array([train[k] for k in meta['training_ids']])
            stats = l.statistics(data, ii)
            for key in stats:
                check('statistics:' + str(p) + ':' + key, np.allclose(stats[key], meta['statistics'][key], rtol=2e-6, atol=2e-6))
            models.append(p)
    im = c.read(c.OUT / 'inference_001/manifest.json')
    check('prediction_hash', c.sha(c.OUT / 'inference_001/predictions_blind.jsonl') == im['predictions_sha256'])
    linked = c.read(c.OUT / 'analysis_001/GT_connection.json')
    check('freeze_before_GT', im['created_utc'] < linked['created_utc'])
    chosen = c.read(c.OUT / 'training_001/selections.json')
    candidates = c.read(c.OUT / 'training_001/cv_metrics.json')
    for family, selection in chosen.items():
        options = [v for v in candidates if v['family'] == family]
        feasible = [v for v in options if v['meets_PA_constraint']]
        rank = lambda v: (v['metrics']['MCC'], v['metrics']['PA'], -v['metrics']['false_S'], -v['hidden'], -v['scale'])
        best = max(feasible or options, key=rank)
        check('training_only_selection:' + family, (best['hidden'], best['scale']) == (selection['hidden'], selection['scale']))
    metrics = c.read(c.OUT / 'analysis_001/metrics.json')
    for name, value in metrics.items():
        cm = np.asarray(value['confusion_matrix'])
        check('confusion_total:' + name, cm.sum() == value['n'])
        check('confusion_correct:' + name, np.trace(cm) == value['correct'])
        check('confusion_falseS:' + name, cm[1:, 0].sum() == value['false_S'])
        check('PA:' + name, abs(np.trace(cm) / cm.sum() - value['PA']) < 1e-12)
    # Train-only scores are selection evidence, never confirmation performance.
    out.mkdir(parents=True)
    summary = dict(created_utc=c.now(), passed=all(checks.values()), count=len(checks), models=len(models), NLI_pairs=len(cache), claims=len(rows), train=len(train), confirmation=len(confirm), new_fits=0, API_calls=0, independent_audit=False)
    c.put(out / 'summary.json', summary)
    c.put(out / 'checks.json', checks)
    print(json.dumps(summary), flush=True)

if __name__ == '__main__':
    main()
