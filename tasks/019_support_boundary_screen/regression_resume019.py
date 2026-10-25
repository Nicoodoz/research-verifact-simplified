"""Continuation regression run with external networking disabled."""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import json
import socket
import sys
import unittest
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/019_support_boundary_screen'
sys.path.insert(0, str(ROOT / 'src'))

def blocked(*args, **kwargs):
    raise RuntimeError('External networking disabled')

if __name__ == '__main__':
    with (OUT / 'full_repository_regression_002.txt').open('x', encoding='utf-8') as log:
        with redirect_stdout(log), redirect_stderr(log), patch.object(socket, 'create_connection', blocked), patch.object(socket.socket, 'connect', blocked):
            suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'))
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    summary = dict(tests=result.testsRun, failures=len(result.failures),
                   errors=len(result.errors), skipped=len(result.skipped),
                   passed=result.wasSuccessful(), network_blocked=True,
                   new_API_calls=0, scope='Existing repository tests after continuation')
    with (OUT / 'full_repository_regression_002.json').open('x', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary), flush=True)
    sys.exit(0 if result.wasSuccessful() else 1)
