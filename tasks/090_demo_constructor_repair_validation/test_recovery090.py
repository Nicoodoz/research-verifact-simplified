"""Isolated disk-ledger recovery checks; no real transport or study writes."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import api090 as api
from common090 import MODEL, put, sha


class Recovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [patch.object(api, 'ROOT', self.root), patch.object(api, 'OUT', self.root)]
        for p in self.patches:
            p.start()
        self.job = api.freeze_job('main', 'B', 'fictional', 'fictional',
            dict(model=MODEL, max_tokens=8, messages=[]))

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def record(self, n, status):
        folder = self.root / 'attempts' / str(n)
        req = folder / 'request.json'
        put(req, dict(job=self.job, attempt_no=n, created_utc='fixture', reserved_cny=0.01))
        if status is not None:
            put(folder / 'receipt.json', dict(request_sha256=sha(req),
                transport=dict(http_status=status, body_text='invalid core fields')))

    def test_successful_invalid_body_is_not_resent(self):
        self.record(1, 200)
        with patch.object(api, 'client', return_value=Mock()), patch.object(api, 'process') as process:
            api.run_jobs([self.job])
            process.assert_not_called()
        self.assertFalse((self.root / 'run.lock').exists())

    def test_resume_preserves_previous_attempt_and_numbers(self):
        self.record(1, 503)
        def recovered(job, past):
            self.assertEqual(past, 1)
            self.record(past + 1, 200)
        with patch.object(api, 'client', return_value=Mock()), patch.object(api, 'process', side_effect=recovered):
            api.run_jobs([self.job])
        rows, success, counts = api.state()
        self.assertEqual([r['attempt_no'] for r in rows], [1, 2])
        self.assertEqual(counts[self.job['request_id']], 2)
        self.assertIn(self.job['request_id'], success)

    def test_unknown_reserve_and_frozen_registration(self):
        self.record(1, None)
        rows, success, counts = api.state()
        self.assertEqual(rows[0]['cost_or_unknown_cny'], 0.01)
        self.assertFalse(success)
        self.assertEqual(counts[self.job['request_id']], 1)
        self.assertEqual(api.freeze_job('main', 'B', 'fictional', 'fictional', self.job['body']), self.job)
        self.assertEqual(len(list((self.root / 'registered_jobs').glob('*.json'))), 1)


if __name__ == '__main__':
    unittest.main()
