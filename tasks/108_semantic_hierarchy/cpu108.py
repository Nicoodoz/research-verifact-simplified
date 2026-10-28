"""Actual fixed-feature classification: three small heads, no encoder training.

Epoch selection uses only the provided train40 internal patient validation.
The500 development cases are inferred once per arm after epoch selection.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import time

import numpy as np
import torch
from torch.nn import functional as F

from model108 import Head, MODES, minimal_checks

LABELS = ('Supported', 'Not Supported', 'Not Addressed')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '092_task_adapted_verifier'))
from metrics092 import metrics


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    temporary.replace(path)


class Data:
    def __init__(self, specification):
        self.specification = specification
        all_rows = {row['id']: row for row in rows(specification['rows_path'])}
        all_bags = {row['id']: row for row in rows(specification['bags_path'])}
        self.splits = read(specification['split_path'])
        keys = ('train', 'validation', 'selection')
        identifiers = [identifier for key in keys for identifier in self.splits[key]]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Train/validation/selection IDs overlap')
        self.rows = {identifier: all_rows[identifier] for identifier in identifiers}
        patients = {key: {self.rows[identifier]['sid'] for identifier in self.splits[key]} for key in keys}
        if patients['train'] & patients['validation'] or (patients['train'] | patients['validation']) & patients['selection']:
            raise ValueError('Patient isolation failed')
        if len(self.splits['selection']) != 500:
            raise ValueError('Exactly500 fixed development cases required')
        source = np.load(specification['feature_path'], mmap_mode='r')
        if source.ndim != 2 or source.shape[1] != 1024:
            raise ValueError('Original cls24 must have1024-wide window features')
        used = sorted({index for identifier in identifiers for index in all_bags[identifier]['windows']})
        lookup = {index: local for local, index in enumerate(used)}
        self.features = torch.from_numpy(np.array(source[used], dtype=np.float32))
        self.bags = {identifier: torch.tensor([lookup[index] for index in all_bags[identifier]['windows']], dtype=torch.long)
                     for identifier in identifiers}
        if any(not len(indices) for indices in self.bags.values()) or not bool(torch.isfinite(self.features).all()):
            raise ValueError('Empty bag/nonfinite original feature')

    def batch(self, identifiers):
        lengths = torch.tensor([len(self.bags[identifier]) for identifier in identifiers], dtype=torch.long)
        indices = torch.cat([self.bags[identifier] for identifier in identifiers])
        groups = torch.repeat_interleave(torch.arange(len(identifiers)), lengths)
        target = torch.tensor([LABELS.index(self.rows[identifier]['GT']) for identifier in identifiers], dtype=torch.long)
        return self.features[indices], groups, target

    def predict(self, head, identifiers, batch_size):
        head.eval()
        probabilities = []
        with torch.inference_mode():
            for start in range(0, len(identifiers), batch_size):
                features, groups, _ = self.batch(identifiers[start:start + batch_size])
                probabilities.append(head(features, groups).exp().numpy())
        return np.concatenate(probabilities)

    def evaluate(self, identifiers, probabilities):
        target = np.array([LABELS.index(self.rows[identifier]['GT']) for identifier in identifiers])
        return metrics(target, probabilities.argmax(1), probabilities)


def train(data, mode, settings, public, private):
    seed = settings['seed']
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    order_rng = np.random.default_rng(seed)
    head = Head(mode, dropout=settings['dropout'])
    optimizer = torch.optim.AdamW(head.parameters(), lr=settings['head_lr'], weight_decay=settings['weight_decay'])
    identifiers = data.splits['train']
    validation = data.splits['validation']
    batch_size = settings['batch_size']
    history = []
    best = None
    begin = time.perf_counter()
    updates = 0
    for epoch in range(1, settings['epochs'] + 1):
        order = order_rng.permutation(len(identifiers))
        head.train()
        total_loss = 0.
        for start in range(0, len(order), batch_size):
            chosen = [identifiers[int(index)] for index in order[start:start + batch_size]]
            features, groups, targets = data.batch(chosen)
            optimizer.zero_grad(set_to_none=True)
            loss = F.nll_loss(head(features, groups), targets)
            if not bool(torch.isfinite(loss)):
                raise FloatingPointError('Nonfinite real classification loss')
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(head.parameters(), settings['gradient_clip'])
            if not bool(torch.isfinite(norm)):
                raise FloatingPointError('Nonfinite head gradient')
            optimizer.step()
            updates += 1
            total_loss += float(loss.detach()) * len(chosen)
        probabilities = data.predict(head, validation, max(batch_size, 64))
        values = data.evaluate(validation, probabilities)
        key = (values['MCC'], values['PA'], values['Macro_F1'], -values['false_S'])
        history.append(dict(epoch=epoch, training_NLL=total_loss / len(identifiers), validation=values))
        if best is None or key > best['key']:
            best = dict(epoch=epoch, key=key, state=deepcopy(head.state_dict()))
        print(json.dumps(dict(arm=mode, epoch=epoch, validation_MCC=values['MCC'], validation_PA=values['PA'], best_epoch=best['epoch'])), flush=True)
    head.load_state_dict(best.pop('state'))
    private.mkdir(parents=True, exist_ok=True)
    torch.save(dict(arm=mode, head=head.state_dict(), settings=settings, selected_epoch=best['epoch'], encoder_trained=False), private / (mode + '.pt'))
    selection = data.splits['selection']
    inference_begin = time.perf_counter()
    probabilities = data.predict(head, selection, max(batch_size, 64))
    inference_seconds = time.perf_counter() - inference_begin
    predictions = [dict(id=identifier, sid=data.rows[identifier]['sid'], GT=data.rows[identifier]['GT'],
                        panel=data.rows[identifier].get('panel'), arm=mode, prediction=LABELS[int(probability.argmax())],
                        probabilities=probability.tolist()) for identifier, probability in zip(selection, probabilities)]
    if mode != 'flat_ce':
        for row in predictions:
            addressed = row['probabilities'][0] + row['probabilities'][1]
            row.update(addressed_probability=addressed,
                       conditional_supported_given_addressed=row['probabilities'][0] / addressed if addressed else None,
                       branch_values_source='factorization_of_saved_joint_probabilities_no_extra_inference')
    panels = {}
    for panel in sorted({row.get('panel') or 'all' for row in predictions}):
        indices = [i for i, row in enumerate(predictions) if (row.get('panel') or 'all') == panel]
        panels[panel] = data.evaluate([selection[i] for i in indices], probabilities[indices])
    public.mkdir(parents=True, exist_ok=True)
    with (public / (mode + '_predictions.jsonl')).open('wb') as stream:
        for row in predictions:
            stream.write((json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))
    result = dict(arm=mode, selected_epoch=best['epoch'], selection_rule='train40_inner_patient_validation_MCC_PA_MacroF1_minus_falseS',
                  validation_best_key=list(best['key']), history=history, panels=panels,
                  seconds=time.perf_counter() - begin, inference_seconds=inference_seconds,
                  optimizer_updates=updates, trainable_parameters=sum(parameter.numel() for parameter in head.parameters()),
                  training_rows=len(identifiers), validation_rows=len(validation), final_selection_rows=len(selection),
                  selection_inferences_per_arm=1, encoder_trained=False, feature_source='original_pretrained_cls24_1024',
                  old_supervised_checkpoint_used=False)
    put(public / (mode + '_training.json'), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--private', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    torch.set_num_threads(args.threads)
    settings = dict(seed=92027, epochs=5, head_lr=.001, weight_decay=.01, dropout=.1, batch_size=8, gradient_clip=1.)
    specification = read(args.data)
    settings.update(specification.get('settings', {}))
    checks = minimal_checks()
    data = Data(specification)
    results = [train(data, mode, settings, args.out, args.private) for mode in MODES]
    summary = dict(task=108, scope='actual_original_pretrained_fixed_feature_CPU_classification', settings=settings,
                   mathematical_checks=checks, arms=results, CUDA_initialized=torch.cuda.is_initialized(),
                   paid_API_calls=0, GPU_training_started=False, confirms_generalization=False,
                   limitation='CPU fixed-feature heads test classification signal; no encoder adaptation or untouched holdout claim')
    put(args.out / 'cpu_summary.json', summary)
    print(json.dumps(dict(complete=True, output=str(args.out / 'cpu_summary.json'))), flush=True)


if __name__ == '__main__':
    main()
