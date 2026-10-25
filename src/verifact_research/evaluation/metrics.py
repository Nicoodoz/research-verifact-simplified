"""Independent nominal-label metrics; no author implementation is imported.

PA is item-weighted exact agreement. AC1 uses pooled category proportions and
chance term sum(p * (1-p)) / (K-1). MCC is the multiclass confusion-matrix form.
Rows of confusion matrices are ground truth; columns are predictions.
"""
from __future__ import annotations

import numpy as np

LABELS = ("Supported", "Not Supported", "Not Addressed")
METRICS = ("percent_agreement", "gwet_ac1", "mcc")


def encode(labels) -> np.ndarray:
    lookup = {label: i for i, label in enumerate(LABELS)}
    try:
        return np.array([lookup[value] for value in labels], dtype=np.int64)
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Unknown label; use exactly {LABELS}") from exc


def confusion(y_true, y_pred) -> np.ndarray:
    true, pred = encode(y_true), encode(y_pred)
    if len(true) != len(pred) or not len(true):
        raise ValueError("Expected equal nonzero numbers of truth and prediction labels")
    return np.bincount(3 * true + pred, minlength=9).reshape(3, 3)


def metrics_from_confusions(matrices: np.ndarray) -> np.ndarray:
    """Vectorized (..., K, K) -> (..., 3): PA, AC1, MCC.

    A constant true or predicted label makes MCC's denominator zero; return 0,
    matching sklearn 1.6.1. Undefined per-class ratios are handled separately.
    """
    c = np.asarray(matrices, dtype=float)
    k = c.shape[-1]
    if c.ndim < 2 or c.shape[-2] != k or k < 2 or np.any(c < 0) or not np.isfinite(c).all():
        raise ValueError("Expected nonnegative finite square confusion matrices")
    total = c.sum(axis=(-1, -2))
    if np.any(total <= 0):
        raise ValueError("Cannot evaluate an empty cohort")
    correct = np.trace(c, axis1=-2, axis2=-1)
    true, pred = c.sum(axis=-1), c.sum(axis=-2)
    pa = correct / total
    p = (true + pred) / (2 * total[..., None])
    pe = (p * (1 - p)).sum(axis=-1) / (k - 1)
    ac1 = (pa - pe) / (1 - pe)
    denominator = np.sqrt(np.maximum(0, (total**2 - (true**2).sum(axis=-1)) *
                                    (total**2 - (pred**2).sum(axis=-1))))
    numerator = correct * total - (true * pred).sum(axis=-1)
    mcc = np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator != 0)
    return np.stack((pa, ac1, mcc), axis=-1)


def classification_metrics(y_true, y_pred) -> dict:
    c = confusion(y_true, y_pred)
    n = int(c.sum())
    result = dict(zip(METRICS, map(float, metrics_from_confusions(c))))
    result.update(n=n, labels=list(LABELS), confusion_matrix=c.tolist())
    classes = {}
    for i, label in enumerate(LABELS):
        tp, fn, fp = int(c[i, i]), int(c[i].sum() - c[i, i]), int(c[:, i].sum() - c[i, i])
        tn = n - tp - fn - fp
        ratio = lambda a, b: a / b if b else None
        classes[label] = dict(support=tp + fn, predicted=tp + fp, tp=tp, fn=fn, fp=fp, tn=tn,
                              recall=ratio(tp, tp + fn), precision=ratio(tp, tp + fp),
                              specificity=ratio(tn, tn + fp), npv=ratio(tn, tn + fn),
                              f1=ratio(2 * tp, 2 * tp + fp + fn))
    result["per_class"] = classes
    result["mcc_denominator_zero"] = bool(np.count_nonzero(c.sum(axis=0)) == 1 or
                                          np.count_nonzero(c.sum(axis=1)) == 1)
    return result


def clinician_metrics(votes: np.ndarray) -> np.ndarray:
    """Exactly three initial clinician votes per item; identities may vary.

    Input is N x 3 encoded labels. Returns PA and AC1, each item weighted equally.
    """
    votes = np.asarray(votes)
    if votes.ndim != 2 or votes.shape[1] != 3 or not len(votes) or not np.isin(votes, range(3)).all():
        raise ValueError("Expected N x 3 valid encoded initial clinician votes")
    pa = ((votes[:, 0] == votes[:, 1]).mean() + (votes[:, 0] == votes[:, 2]).mean() +
          (votes[:, 1] == votes[:, 2]).mean()) / 3
    p = np.bincount(votes.ravel(), minlength=3) / votes.size
    pe = np.sum(p * (1 - p)) / 2
    return np.array([pa, (pa - pe) / (1 - pe)])


def interval(draws: np.ndarray) -> list[float]:
    if not len(draws) or not np.isfinite(draws).all():
        raise ValueError("All bootstrap draws must be finite")
    return np.percentile(draws, [2.5, 97.5], method="linear").tolist()


def item_bootstrap(codes: np.ndarray, iterations: int) -> np.ndarray:
    """Exact pandas sample(frac=1, replace=True, random_state=i) draw sequence."""
    if iterations < 1:
        raise ValueError("Bootstrap iterations must be positive")
    counts = np.empty((iterations, 3, 3), dtype=np.int64)
    for i in range(iterations):
        sample = np.random.RandomState(i).choice(len(codes), size=len(codes), replace=True)
        counts[i] = np.bincount(codes[sample], minlength=9).reshape(3, 3)
    return metrics_from_confusions(counts)


def patient_bootstrap(codes: np.ndarray, subjects: list[str], iterations: int) -> np.ndarray:
    """Resample patients; retain every sampled patient's propositions with multiplicity.

    Point estimate remains micro/item-weighted; this is NOT a patient-macro score.
    """
    if iterations < 1 or len(subjects) != len(codes) or not len(codes):
        raise ValueError("Expected aligned nonempty subjects and positive iterations")
    unique = sorted(set(subjects))
    if len(unique) < 2:
        raise ValueError("Patient bootstrap requires at least two patients")
    lookup = {s: i for i, s in enumerate(unique)}
    counts = np.zeros((len(unique), 9), dtype=np.int64)
    np.add.at(counts, ([lookup[s] for s in subjects], codes), 1)
    draws = np.empty((iterations, 3, 3), dtype=np.int64)
    for i in range(iterations):
        selected = np.random.RandomState(i).choice(len(unique), len(unique), replace=True)
        draws[i] = counts[selected].sum(axis=0).reshape(3, 3)
    return metrics_from_confusions(draws)
