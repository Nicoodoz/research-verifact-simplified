"""Offline CPU/API environment smoke test; no keys, models, patient data or writes."""
import importlib.metadata
import json
import os
import socket
import sys
def denied(*args, **kwargs):
    raise RuntimeError("Environment check is offline")
socket.create_connection = denied
socket.socket.connect = denied
import numpy as np
from scipy.optimize import minimize
from scipy.special import logsumexp
def quadratic(x):
    delta = x - np.array([1., 2.])
    return float(delta @ delta), 2 * delta
results = {}
for method in ("L-BFGS-B", "SLSQP"):
    fit = minimize(quadratic, [0., 0.], jac=True, method=method,
                   bounds=[(-5., 5.), (-5., 5.)])
    assert fit.success and np.allclose(fit.x, [1., 2.], atol=1e-7)
    results[method] = {"success": bool(fit.success), "objective": float(fit.fun)}
rng = np.random.RandomState(35035)
x = rng.normal(size=(256, 384))
y = rng.normal(size=(384, 128))
assert np.allclose(x @ y, np.einsum("ik,kj->ij", x, y, optimize=False),
                   atol=1e-10, rtol=1e-10)
assert np.isfinite(logsumexp(x, axis=1)).all()
assert os.environ.get("CONDA_DEFAULT_ENV") == "research-verifact-029", "Use scripts/run_research.ps1"
assert sys.prefix.replace("\\", "/").lower().endswith("/research-verifact-029")
print(json.dumps({
    "passed": True, "executable": sys.executable,
    "conda_environment": os.environ.get("CONDA_DEFAULT_ENV"),
    "versions": {k: importlib.metadata.version(k) for k in
                 ("numpy", "scipy", "pandas", "scikit-learn", "duckdb", "matplotlib")},
    "optimizers": results, "matrix_multiply": "matches scalar contraction",
    "network": "blocked", "API_calls": 0
}, indent=2))
