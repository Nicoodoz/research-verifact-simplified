"""One fixed106 TF-IDF/LR fit on40 training patients, matched1817 diagnosis."""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys
import time
import warnings

import joblib
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / '.local_models/123_claim_only_control'
sys.path.insert(0, str(ROOT / 'tasks/105_brief_supervision'))
import common105 as common
sys.path.insert(0, str(ROOT / 'tasks/116_research_cycle'))
from analyze_scores116 import section
from prepare123 import inputs_and_metadata


def run():
    out = PRIVATE / 'tfidf_control'
    if out.exists() and any(out.iterdir()):
        raise FileExistsError('Preserve the one fixed TF-IDF attempt')
    inputs, metadata, parts = inputs_and_metadata()
    claims = {r['id']: r['claim'] for r in inputs}
    train = parts['train']; screen = parts['screen']
    keys = {r['id']:r for r in common.rows(ROOT / '.local_models/116_research_cycle/keys_selection1817.jsonl')}
    base = {r['id']:r for r in common.rows(ROOT / '.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
    full = {r['id']:r for r in common.rows(ROOT / '.local_models/118_full_data_heads/reconsidered_refit/sqrt_weight_full/predictions.jsonl')}
    if set(keys) != {r['id'] for r in screen} or set(full) != set(keys) or set(base) != set(keys):
        raise ValueError('The matched1817 comparison is incomplete')
    model = make_pipeline(
        TfidfVectorizer(lowercase=True, ngram_range=(1,2), min_df=2, max_features=30000, sublinear_tf=True),
        LogisticRegression(C=1., max_iter=1000, solver='lbfgs', random_state=106))
    out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    with threadpool_limits(limits=4), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', ConvergenceWarning)
        model.fit([claims[r['id']] for r in train], [r['GT'] for r in train])
        labels = model.predict([claims[r['id']] for r in screen])
        probabilities = model.predict_proba([claims[r['id']] for r in screen])
    predicted = {r['id']:dict(id=r['id'], verdict=str(label), valid=True,
        probabilities=dict(zip(model.classes_.tolist(), p.tolist())), probabilities_calibrated=False)
        for r, label, p in zip(screen, labels, probabilities)}
    joblib.dump(model, out / 'model.joblib')
    common.putl(out / 'predictions_sanitized.jsonl', [dict(predicted[i], sid=str(keys[i]['sid']),
        GT=keys[i]['GT'], author=keys[i]['author'], old_panel=keys[i].get('old_panel'),
        subset=keys[i].get('subset')) for i in sorted(keys)])
    groups = dict(selection1817=list(keys.values()),
        new1317=[r for r in keys.values() if r.get('subset') == 'new'],
        natural400=[r for r in keys.values() if r.get('old_panel') == 'natural'],
        pressure100=[r for r in keys.values() if r.get('old_panel') == 'pressure'])
    panels = {name:section(rows, base, predicted) for name, rows in groups.items()}
    from analyze109 import metrics
    for name, rows in groups.items():
        panels[name]['scores']['full_reference_sqrt118'] = metrics(rows, {r['id']: full[r['id']]['verdict'] for r in rows})
    result = dict(task=123, candidate='tfidf_claim_only_control', fixed106_recipe=True,
        train_N=len(train), train_patients=len({r['sid'] for r in train}),
        screen_N=len(screen), screen_patients=len({r['sid'] for r in screen}),
        train_GT=dict(Counter(r['GT'] for r in train)), screen_GT=dict(Counter(r['GT'] for r in screen)),
        new_GPU_CNY=0, new_API_CNY=0, CPU_seconds=time.perf_counter()-started,
        fit_count=1, hyperparameter_search=False, old106_OOF_unchanged=True,
        converged=not any(issubclass(w.category, ConvergenceWarning) for w in caught),
        warnings=[str(w.message) for w in caught],
        recipe=dict(ngram_range=[1,2], lowercase=True, min_df=2, max_features=30000, sublinear_tf=True,
                    C=1., max_iter=1000, solver='lbfgs', class_weight=None, random_state=106),
        panels=panels, interpretation='A weaker lexical claim-only control; not a substitute for matched frozen107 claim-only features.')
    common.put(out / 'result.json', result)
    print(common.canonical(dict(CPU_seconds=result['CPU_seconds'], converged=result['converged'],
        panels={k:dict(N=v['N'], scores={a:dict(MCC=m['mcc'], PA=m['percent_agreement'],
            correct=m['correct'], false_S=m['false_S']) for a,m in v['scores'].items()}) for k,v in panels.items()})))


if __name__ == '__main__':
    run()
