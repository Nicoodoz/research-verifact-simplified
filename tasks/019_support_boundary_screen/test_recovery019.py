"""Offline recovery checks; no external requests, real keys, or clinical labels."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import atomic019


class RecoveryTests(unittest.TestCase):
    def test_atomic_retry_retains_old_until_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            path.write_text('{"old":true}', encoding='utf-8')
            replace = atomic019.os.replace
            calls = []
            def interrupted(source, target):
                calls.append(1)
                if len(calls) < 3:
                    self.assertEqual(json.loads(path.read_text()), {'old': True})
                    raise PermissionError('simulated sharing conflict')
                return replace(source, target)
            with patch.object(atomic019.os, 'replace', interrupted), patch.object(atomic019.time, 'sleep'):
                atomic019.save(path, {'new': True})
            self.assertEqual(json.loads(path.read_text()), {'new': True})
            self.assertEqual(len(calls), 3)
            self.assertFalse(list(Path(directory).glob('.pending-*')))

    def test_new_file_guard(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            atomic019.save(path, {'answer': 1}, new=True)
            with self.assertRaises(ValueError):
                atomic019.save(path, {'answer': 2}, new=True)
            self.assertEqual(json.loads(path.read_text()), {'answer': 1})

    def test_permanent_failure_preserves_old_and_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'ledger.json'
            path.write_text('{"old":true}', encoding='utf-8')
            with patch.object(atomic019.os, 'replace', side_effect=PermissionError('simulated')), patch.object(atomic019.time, 'sleep'):
                with self.assertRaises(PermissionError):
                    atomic019.save(path, {'new': True})
            self.assertEqual(json.loads(path.read_text()), {'old': True})
            pending = list(Path(directory).glob('.pending-*'))
            self.assertEqual(len(pending), 1)
            self.assertEqual(json.loads(pending[0].read_text()), {'new': True})

    def test_nonfinite_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                atomic019.save(Path(directory) / 'ledger.json', {'x': float('nan')})
            self.assertFalse(list(Path(directory).iterdir()))

if __name__ == '__main__':
    unittest.main()
