"""Additional completion checks; no fitting, network, or confirmation-label selection."""
from pathlib import Path
import json, hashlib, datetime, subprocess
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/032_evidence_relation_correction'
TASK = ROOT / 'tasks/032_evidence_relation_correction'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''): h.update(b)
    return h.hexdigest()
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
checks = {}
prep = read(OUT/'preparation_001/manifest.json')
for name, h in prep['sources'].items(): checks['source:'+name] = sha(ROOT/'outputs'/name) == h
for name, h in prep['files'].items(): checks['prepared:'+name] = sha(OUT/'preparation_001'/name) == h
freeze = read(OUT/'training_001/freeze.json')
for name, h in freeze['code'].items(): checks['training_code:'+name] = sha(TASK/name) == h
checks['frozen_config'] = sha(TASK/'config.json') == sha(OUT/'preparation_001/config.json')
checks['frozen_protocol'] = sha(TASK/'protocol.md') == sha(OUT/'preparation_001/protocol.md')
nli = read(OUT/'nli_001/manifest.json')
checks['nli_training_binding'] = sha(OUT/'nli_001/manifest.json') == freeze['nli_manifest_sha256']
checks['bags_binding'] = sha(ROOT/'.local_models/032/bags.npz') == nli['bags_sha256']
checks['mapping_binding'] = sha(OUT/'nli_001/bags.jsonl') == nli['bag_mapping_sha256']
done = np.load(ROOT/'.local_models/032/pair_cache/done.npy', mmap_mode='r')
features = np.load(ROOT/'.local_models/032/pair_cache/features.npy', mmap_mode='r')
checks['nli_complete_finite'] = bool(np.all(done == 1) and np.isfinite(features).all())
checks['nli_probabilities_sum_one'] = bool(np.allclose(features[:,:3].sum(1), 1, atol=1e-5))
inf = read(OUT/'inference_001/manifest.json')
checks['prediction_binding'] = sha(OUT/'inference_001/predictions_blind.jsonl') == inf['predictions_sha256']
checks['selected_config_binding'] = sha(OUT/'training_001/selections.json') == inf['selections_sha256']
train = set(inf['training_patients']); confirm = set(inf['confirmation_patients'])
checks['patient_split_28_12'] = len(train)==28 and len(confirm)==12 and not bool(train & confirm)
folds = read(OUT/'preparation_001/folds.json')
checks['fold_partition'] = sorted(p for f in folds for p in f['validation_patients']) == sorted(train)
model_paths = list((OUT/'training_001/models').rglob('model.json')) + list((OUT/'inference_001/models').rglob('model.json'))
for p in model_paths:
    m = read(p)
    checks['model:'+str(p.relative_to(OUT))] = set(m['training_patients']) <= train and sha(p.parent/'weights.pt') == m['weights_sha256']
for name, v in read(OUT/'analysis_001/baseline_checks.json').items(): checks['baseline:'+name] = bool(v)
replay = read(OUT/'verification_001/checks.json')
checks['saved_model_replay'] = replay['passed'] and all(replay['checks'].values())
checks['selfcheck'] = read(OUT/'closeout_001/checks.json')['passed']
connection = read(OUT/'analysis_001/GT_connection.json')
checks['prediction_before_evaluation'] = inf['created_utc'] <= connection['created_utc']
nav_before = read(OUT/'continuation_navigation_before_001.json')
for name in ['.gitignore', 'environment.yml']:
    if name in nav_before: checks['protected:'+name] = sha(ROOT/name) == nav_before[name]
changed = subprocess.check_output(['git','diff','--name-only','HEAD','--','tasks','outputs'],cwd=ROOT,text=True).splitlines()
checks['git_tracked_historical_unchanged'] = all(p.startswith(('tasks/032_', 'outputs/032_')) for p in changed)
assert all(checks.values()), [k for k,v in checks.items() if not v]
result = dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), passed=True, checks=checks, model_count=len(model_paths), nli_pairs=len(done), no_new_fits_in_this_check=True, API_calls=0, independent_audit=False)
save(OUT/'completion_verification_001.json', result)
files = {str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted(OUT.rglob('*')) if p.is_file() and p not in [OUT/'manifest.json', OUT/'handoff_001.json'] and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo']}
files.update({str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in TASK.iterdir() if p.is_file()})
save(OUT/'manifest.json', dict(utc=result['utc'], status='completed_pending_independent_audit', files=files, external_cache=nli, independent_audit=False))
handoff = dict(status='completed_pending_independent_audit', utc=result['utc'], independent_audit=False, new_paid_API_calls=0, reserved_test_used=False, source_git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), commit_or_push_performed=False, checks_count=len(checks), model_count=len(model_paths), manifest_sha256=sha(OUT/'manifest.json'), report_sha256=sha(OUT/'report.md'), main_metrics=read(OUT/'analysis_001/metrics.json')['all/attention'])
save(OUT/'handoff_001.json', handoff)
print(json.dumps(dict(status=handoff['status'], checks=len(checks), models=len(model_paths), nli_pairs=len(done), main_metrics=handoff['main_metrics'], independent_audit=False),ensure_ascii=False))
