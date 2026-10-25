"""Identifiable paired three-class scaling models for 082; no file or API access."""
from __future__ import annotations

import math
from collections import Counter

import numpy as np
from scipy.optimize import minimize

LABELS = ("Supported", "Not Supported", "Not Addressed")
FAMILIES = ("independent", "shared", "adapted")
REG_GRID = (0.01, 0.1, 1.0)
TIE_ORDER = np.array([1, 2, 0])  # historical NS > NA > S


def log_scores(rows):
    score = np.asarray([[[float(row[arm][lab]) for lab in LABELS] for arm in ("B", "F4")]
                        for row in rows], dtype=float)
    assert score.ndim == 3 and score.shape[1:] == (2, 3)
    assert np.all(np.isfinite(score)) and np.all(score >= 0)
    assert np.all(np.abs(score.sum(axis=2) - 100) < 1e-5)
    return np.log(np.maximum(score / 100, 1e-6))


def patient_weights(rows):
    count = Counter(x["sid"] for x in rows)
    assert count
    value = np.array([1 / (len(count) * count[x["sid"]]) for x in rows], dtype=float)
    assert np.isclose(value.sum(), 1)
    return value


def num_parameters(family):
    return {"independent": 10, "shared": 5, "adapted": 7}[family]


def penalty_weights(family):
    return np.asarray([1] * 10 if family == "independent" else [1] * 5 if family == "shared"
                      else [1] * 5 + [4] * 2, dtype=float)


def logits(z, theta, family):
    if family == "independent":
        d0 = np.exp(theta[:3]); b0 = np.r_[theta[3:5], 0.0]
        d1 = np.exp(theta[5:8]); b1 = np.r_[theta[8:10], 0.0]
        return np.stack((z[:, 0, :] * d0 + b0, z[:, 1, :] * d1 + b1), axis=1)
    d = np.exp(theta[:3]); b = np.r_[theta[3:5], 0.0]
    value = z * d + b
    if family == "adapted":
        value[:, 1, :] += np.r_[theta[5:7], 0.0]
    return value


def objective(theta, z, y, weight, family, regularization):
    assert family in FAMILIES and len(theta) == num_parameters(family)
    value = logits(z, theta, family)
    top = value.max(axis=2, keepdims=True)
    exp = np.exp(value - top)
    probs = exp / exp.sum(axis=2, keepdims=True)
    correct = value[np.arange(len(y)), :, y]
    logsum = top[:, :, 0] + np.log(exp.sum(axis=2))
    loss = float(np.sum(weight * np.mean(logsum - correct, axis=1)))
    residual = probs - np.eye(3)[y, None, :]
    residual *= weight[:, None, None] / 2
    grad = np.zeros(len(theta), dtype=float)
    if family == "independent":
        grad[:3] = np.sum(residual[:, 0, :] * (z[:, 0, :] * np.exp(theta[:3])), axis=0)
        grad[3:5] = np.sum(residual[:, 0, :2], axis=0)
        grad[5:8] = np.sum(residual[:, 1, :] * (z[:, 1, :] * np.exp(theta[5:8])), axis=0)
        grad[8:10] = np.sum(residual[:, 1, :2], axis=0)
    else:
        grad[:3] = np.sum(residual * (z * np.exp(theta[:3])), axis=(0, 1))
        grad[3:5] = np.sum(residual[:, :, :2], axis=(0, 1))
        if family == "adapted":
            grad[5:7] = np.sum(residual[:, 1, :2], axis=0)
    pw = penalty_weights(family)
    loss += float(regularization * np.sum(pw * theta**2) / (2 * len(theta)))
    grad += regularization * pw * theta / len(theta)
    return loss, grad


def fit(rows, family, regularization):
    assert rows and family in FAMILIES and regularization in REG_GRID
    z = log_scores(rows)
    y = np.array([LABELS.index(x["GT"]) for x in rows], dtype=int)
    w = patient_weights(rows)
    initial = np.zeros(num_parameters(family), dtype=float)
    bounds = [(-1.6, 1.6)] * len(initial)
    for j in range(len(initial)):
        if j in ((3, 4, 8, 9) if family == "independent" else (3, 4)):
            bounds[j] = (-4.0, 4.0)
        if family == "adapted" and j >= 5:
            bounds[j] = (-2.0, 2.0)
    f = lambda t: objective(t, z, y, w, family, regularization)
    first = minimize(f, initial, jac=True, bounds=bounds, method="L-BFGS-B",
                     options={"maxiter": 300, "ftol": 1e-12, "gtol": 1e-8})
    tries = [{"solver": "L-BFGS-B", "success": bool(first.success), "message": str(first.message)}]
    result = first
    if not first.success:
        result = minimize(f, first.x, jac=True, bounds=bounds, method="SLSQP",
                          options={"maxiter": 300, "ftol": 1e-11})
        tries.append({"solver": "SLSQP", "success": bool(result.success), "message": str(result.message)})
    baseline, _ = f(initial)
    final, gradient = f(result.x)
    assert np.all(np.isfinite(result.x)) and final <= baseline + 1e-7, (family, regularization, tries)
    projected = gradient.copy()
    for j, (lo, hi) in enumerate(bounds):
        if result.x[j] <= lo + 1e-6:
            projected[j] = min(projected[j], 0)
        if result.x[j] >= hi - 1e-6:
            projected[j] = max(projected[j], 0)
    assert np.max(np.abs(projected)) < 1e-3, (family, regularization, tries, projected)
    return {"family": family, "regularization": regularization,
            "theta": result.x.tolist(), "n_labels": len(rows),
            "n_patients": len({x["sid"] for x in rows}),
            "training_ids": [x["id"] for x in rows],
            "objective": final, "unfitted_objective": baseline,
            "projected_gradient_max": float(np.max(np.abs(projected))),
            "optimizer": tries, "parameter_count": len(result.x),
            "weight_rule": "equal total weight per calibration patient; paired B/F4 loss averaged per independent claim"}


def predict(rows, model):
    z = log_scores(rows)
    value = logits(z, np.asarray(model["theta"], dtype=float), model["family"])
    return TIE_ORDER[np.argmax(value[:, :, TIE_ORDER], axis=2)]


def probability(rows, model):
    value = logits(log_scores(rows), np.asarray(model["theta"], dtype=float), model["family"])
    top = value.max(axis=2, keepdims=True)
    exp = np.exp(value - top)
    return exp / exp.sum(axis=2, keepdims=True)


def finite_difference_check(rows):
    z = log_scores(rows)
    y = np.array([LABELS.index(x["GT"]) for x in rows], dtype=int)
    w = patient_weights(rows)
    checks = {}
    for family in FAMILIES:
        theta = np.linspace(-0.15, 0.17, num_parameters(family))
        _, gradient = objective(theta, z, y, w, family, 0.1)
        numerical = []
        for j in range(len(theta)):
            step = np.zeros(len(theta)); step[j] = 1e-6
            numerical.append((objective(theta + step, z, y, w, family, 0.1)[0]
                              - objective(theta - step, z, y, w, family, 0.1)[0]) / 2e-6)
        error = float(np.max(np.abs(gradient - numerical)))
        assert error < 1e-6, (family, error)
        checks[family] = error
    return checks
