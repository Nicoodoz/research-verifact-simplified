"""Six fixed CPU RBF-SVM probes; only internal validation chooses models.

Default execution fits on1024 and validates on730 cached verdict-prefix states,
then evaluates the pre-frozen160 IDs.  --extend500 reuses saved choices without
refitting; it is a separate, conditional entry point and is never automatic.
No language model, GPU, API, probability calibration or threshold search.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

import joblib
import numpy as np
from sklearn.metrics.pairwise import rbf_kernel
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from threadpoolctl import threadpool_limits

from fit_probe117 import LABELS, metadata_rows, metrics, write_json

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/117_verdict_probe'
PUBLIC = ROOT / 'outputs/117_verdict_probe'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT / 'tasks/116_research_cycle'))
from analyze_scores116 import section

CS = (.1, 1., 10.)
CLASS_WEIGHTS = (None, 'balanced')
FEATURE = 'verdict_prefix'


def load_features(directories, identifiers):
    wanted = set(identifiers)
    found = {}
    width = None
    files_read = 0
    for directory in directories:
        for path in sorted((directory / 'batches').glob('*.npz')):
            with np.load(path, allow_pickle=False) as saved:
                ids = np.asarray(saved['ids']).astype(str).tolist()
                if len(ids) != len(set(ids)):
                    raise ValueError('Duplicate feature IDs in ' + path.name)
                selected = [i for i, identifier in enumerate(ids) if identifier in wanted]
                if not selected:
                    continue
                values = np.asarray(saved[FEATURE], dtype=np.float64)
                if values.ndim != 2 or len(values) != len(ids) or not np.isfinite(values).all():
                    raise ValueError('Invalid verdict-prefix features in ' + path.name)
                if width is None:
                    width = values.shape[1]
                if not width or values.shape[1] != width:
                    raise ValueError('Feature dimension changed')
                for index in selected:
                    identifier = ids[index]
                    if identifier in found:
                        raise ValueError('Feature ID appears in multiple files: ' + identifier)
                    found[identifier] = values[index].copy()
                files_read += 1
    absent = wanted - set(found)
    if absent:
        raise ValueError(f'Missing {len(absent)} cached feature IDs')
    return np.stack([found[identifier] for identifier in identifiers]), dict(
        feature=FEATURE, width=width, requested_N=len(identifiers), batch_files_read=files_read)


def rank(config):
    value = config['validation_metrics']
    return value['mcc'], value['percent_agreement'], -value['false_S'], -config['index']


def fit(metadata, directories, out, threads, deadline):
    rows = metadata_rows(metadata)
    groups = {role: [r for r in rows if r['role'] == role]
              for role in ('train', 'validation', 'screen')}
    if (len(groups['train']), len(groups['validation']), len(groups['screen'])) != (1024, 730, 160):
        raise ValueError('This fixed initial screening requires1024/730/160 metadata rows')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Preserve existing kernel outputs; use --extend500 or inspect before refitting')
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    def budget():
        if time.perf_counter() >= deadline:
            raise TimeoutError('CPU kernel screening reached its five-minute limit')

    try:
        budget()
        # Screen features/labels do not enter scaler fit, kernel scale or selection.
        fitting = groups['train'] + groups['validation']
        matrix, feature_info = load_features(directories, [r['id'] for r in fitting])
        count = len(groups['train'])
        scaler = StandardScaler().fit(matrix[:count])
        train_x = np.ascontiguousarray(scaler.transform(matrix[:count]))
        validation_x = scaler.transform(matrix[count:])
        variance = float(train_x.var())
        if variance <= 0 or not np.isfinite(variance):
            raise ValueError('Training features have no finite variance')
        gamma = 1.0 / (train_x.shape[1] * variance)
        # Exactly the RBF kernel used by SVC(gamma='scale'), computed once for
        # all six configurations.  This changes compute reuse, not the model.
        train_kernel = rbf_kernel(train_x, train_x, gamma=gamma)
        validation_kernel = rbf_kernel(validation_x, train_x, gamma=gamma)
        train_y = np.asarray([r['GT'] for r in groups['train']])
        configurations = []
        models = []
        write_json(out / 'protocol.json', dict(feature=FEATURE, C=CS,
                   gamma_policy='scale', actual_gamma=gamma, class_weights=CLASS_WEIGHTS,
                   probability=False, threshold_search=False,
                   selection='validation MCC, PA, fewer false-S, earlier fixed configuration',
                   primary_family='balanced', training_N=count,
                   validation_N=len(groups['validation']), initial_screen_N=160))
        for c in CS:
            for weight in CLASS_WEIGHTS:
                budget()
                began = time.perf_counter()
                model = SVC(C=c, kernel='precomputed', class_weight=weight,
                            probability=False, cache_size=256)
                model.fit(train_kernel, train_y)
                value = metrics(groups['validation'], model.predict(validation_kernel))
                row = dict(index=len(configurations), C=c, gamma='scale',
                           actual_gamma=gamma, class_weight=weight,
                           validation_metrics=value, fit_status=int(model.fit_status_),
                           iterations=model.n_iter_.tolist(), support_vectors=len(model.support_),
                           seconds=time.perf_counter()-began)
                if model.fit_status_ != 0:
                    raise RuntimeError('SVM did not converge under the unchanged fixed configuration')
                configurations.append(row)
                models.append(model)
                with (out / 'fit_log.jsonl').open('ab') as stream:
                    stream.write((json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n').encode())
                print(json.dumps(dict(config=row['index'], C=c, class_weight=weight,
                           validation_MCC=value['mcc'], seconds=row['seconds'])), flush=True)
        best = max(configurations, key=rank)
        balanced = max((r for r in configurations if r['class_weight'] == 'balanced'), key=rank)
        indices = {'rbf_balanced': balanced['index']}
        if best['index'] != balanced['index']:
            indices['rbf_overall'] = best['index']
        budget()
        np.savez_compressed(out / 'geometry.npz', train_x=train_x,
                            mean=scaler.mean_, scale=scaler.scale_, gamma=np.asarray(gamma),
                            train_ids=np.asarray([r['id'] for r in groups['train']]),
                            labels=np.asarray(LABELS))
        files = {}
        for name, index in indices.items():
            filename = f'model_config_{index}.joblib'
            joblib.dump(models[index], out / filename, compress=3)
            files[name] = filename
        selection = dict(feature=FEATURE, configurations=configurations,
                         selected_indices=indices, model_files=files,
                         overall_config_index=best['index'], balanced_config_index=balanced['index'],
                         overall_alias='rbf_balanced' if best['index'] == balanced['index'] else 'rbf_overall',
                         primary='rbf_balanced', selection_uses_screen=False,
                         gamma='scale', actual_gamma=gamma,
                         kernel_implementation='exact cached RBF; SVC precomputed',
                         feature_info=feature_info,
                         split={role: dict(N=len(part), patients=len({str(r['sid']) for r in part}))
                                for role, part in groups.items()},
                         elapsed_seconds=time.perf_counter()-started)
        # Freeze both choices before calculating any screen prediction.
        write_json(out / 'selection.json', selection)
        return selection, groups['screen']
    except BaseException as error:
        write_json(out / 'status.json', dict(status='stopped', error=repr(error),
                   elapsed_seconds=time.perf_counter()-started, no_GPU=True))
        raise


def evaluate_saved(selection, screen_rows, directories, out, public_path, deadline, phase):
    if time.perf_counter() >= deadline:
        raise TimeoutError('CPU screening limit reached before evaluation')
    ids = [r['id'] for r in screen_rows]
    raw, feature_info = load_features(directories, ids)
    with np.load(out / 'geometry.npz', allow_pickle=False) as saved:
        if tuple(saved['labels'].astype(str)) != tuple(LABELS):
            raise ValueError('Saved kernel label schema differs')
        train_x = saved['train_x']
        scaled = (raw - saved['mean']) / saved['scale']
        gamma = float(saved['gamma'])
    kernel = rbf_kernel(scaled, train_x, gamma=gamma)
    wanted = set(ids)
    key_rows = [r for r in common.rows(ROOT / '.local_models/116_research_cycle/keys_selection1817.jsonl')
                if r['id'] in wanted]
    keys = {r['id']: r for r in key_rows}
    base = {r['id']: r for r in common.rows(ROOT / '.local_models/116_research_cycle/baseline107_selection1817.jsonl')
            if r['id'] in wanted}
    if set(keys) != wanted or set(base) != wanted:
        raise ValueError('Missing original107 baseline or evaluation metadata')
    if any(keys[r['id']]['GT'] != r['GT'] or str(keys[r['id']]['sid']) != str(r['sid']) for r in screen_rows):
        raise ValueError('Original GT/patient association changed')
    result = dict(name='kernel_probe_' + phase, primary='rbf_balanced',
                  models={}, validation_configurations=selection['configurations'],
                  selected_indices=selection['selected_indices'], overall_alias=selection['overall_alias'],
                  selection_uses_screen=False, feature=FEATURE, gamma='scale', actual_gamma=gamma,
                  probability_calibration=False, no_threshold_search=True,
                  feature_info=feature_info, new_GPU=False, new_API=False,
                  confirmation40_used=False,
                  cohort_scope='fixed160 nested development screen' if phase == '160' else 'original400 natural plus100 pressure')
    for name, filename in selection['model_files'].items():
        if time.perf_counter() >= deadline:
            raise TimeoutError('CPU screening limit reached during evaluation')
        model = joblib.load(out / filename)
        labels = model.predict(kernel)
        predictions = {}
        records = []
        for row, label in zip(screen_rows, labels):
            record = dict(id=row['id'], sid=str(row['sid']), GT=row['GT'],
                          author=row.get('author', keys[row['id']].get('author')),
                          old_panel=keys[row['id']]['old_panel'], verdict=str(label), valid=True,
                          baseline107=base[row['id']]['verdict'], probabilities=None,
                          probability_scope='not available; SVM probability=False')
            predictions[row['id']] = record
            records.append(record)
        groups = {panel: [keys[i] for i in ids if keys[i]['old_panel'] == panel]
                  for panel in ('natural', 'pressure')}
        groups['screen_enriched' if phase == '160' else 'old500_composition'] = [keys[i] for i in ids]
        panels = {panel: section(part, base, predictions) for panel, part in groups.items()}
        index = selection['selected_indices'][name]
        result['models'][name] = dict(N=len(ids), configuration=selection['configurations'][index], panels=panels)
        common.putl(out / f'{name}_predictions_{phase}.jsonl', records)
    write_json(public_path, result)
    write_json(out / ('status_' + phase + '.json'), dict(status='complete', N=len(ids),
               public_result=str(public_path), evaluated_models=list(result['models']),
               no_GPU=True, no_API=True, selected_without_screen=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--features', type=Path, nargs='+')
    parser.add_argument('--metadata', type=Path, default=PRIVATE / 'metadata.jsonl')
    parser.add_argument('--out', type=Path, default=PRIVATE / 'kernel_initial')
    parser.add_argument('--public-output', type=Path)
    parser.add_argument('--extend500', action='store_true')
    parser.add_argument('--threads', type=int, default=4)
    parser.add_argument('--max-seconds', type=float, default=240)
    args = parser.parse_args()
    if args.threads < 1 or not 0 < args.max_seconds <= 300:
        parser.error('Positive CPU threads and at most300 seconds required')
    began = time.perf_counter()
    deadline = began + args.max_seconds
    with threadpool_limits(limits=args.threads):
        if args.extend500:
            selection = common.read(args.out / 'selection.json')
            screen = [r for r in common.rows(ROOT / '.local_models/116_research_cycle/keys_selection1817.jsonl')
                      if r['old_panel'] in ('natural', 'pressure')]
            if len(screen) != 500 or len({r['id'] for r in screen}) != 500:
                raise ValueError('The extension must be the unchanged original500 IDs')
            directories = args.features or [PRIVATE / 'evidence/features_initial',
                                           PRIVATE / 'evidence/features500_missing']
            phase = '500'
        else:
            directories = args.features or [PRIVATE / 'evidence/features_initial']
            selection, screen = fit(args.metadata, directories, args.out, args.threads, deadline)
            phase = '160'
        public_path = args.public_output or PUBLIC / f'kernel_probe_{phase}.json'
        result = evaluate_saved(selection, screen, directories, args.out, public_path, deadline, phase)
    print(json.dumps(dict(phase=phase, elapsed_seconds=time.perf_counter()-began,
              selections=selection['selected_indices'],
              metrics={name: {p: {key: value[key] for key in
                                 ('N', 'delta_MCC', 'delta_PA', 'delta_correct', 'delta_false_S')}
                             for p, value in model['panels'].items()}
                       for name, model in result['models'].items()}), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
