"""Offline regression of budget, direct verdict parsing and frozen arm identities."""
import datetime as dt
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import common098 as c
import runtime098 as rt
from verifact_research.inference.aliyun import Config

def transport(content, start='2026-10-26T14:01:00+00:00', end='2026-10-26T14:01:20+00:00'):
    response = dict(model=c.MODEL, choices=[dict(finish_reason='stop', message=dict(content=content))],
                    usage=dict(prompt_tokens=1000, completion_tokens=100, prompt_tokens_details=dict(cached_tokens=500)))
    return dict(http_status=200, outcome_unknown=False, started_utc=start, ended_utc=end,
                body_text=json.dumps(response))

class Tests(unittest.TestCase):
    def test_verdict_no_score_dependency(self):
        p = c.parse_native(transport('{"verdict":"Not Addressed","reason":"No matching event."}'))
        self.assertTrue(p['valid']); self.assertEqual(p['verdict'], 'Not Addressed')

    def test_duplicate_invalid_and_truncation(self):
        self.assertFalse(c.parse_native(transport('{"verdict":"Supported","verdict":"Not Supported"}'))['valid'])
        self.assertFalse(c.parse_native(transport('{"verdict":"Supported"'))['valid'])

    def test_missing_reason_flag_not_relabel(self):
        p = c.parse_native(transport('{"verdict":"Supported"}'))
        self.assertTrue(p['valid']); self.assertTrue(p['format_anomaly'])

    def test_peak_idle_boundary_and_cache(self):
        tr = transport('{}')
        self.assertAlmostEqual(rt.accounting({}, tr, .1)[0], .001275)
        tr = transport('{}', '2026-10-26T13:59:50+00:00', '2026-10-26T14:00:10+00:00')
        self.assertAlmostEqual(rt.accounting({}, tr, .1)[0], .00255)

    def test_unknown_keeps_full_reservation(self):
        self.assertEqual(rt.accounting({}, dict(http_status=0), .17)[0], .17)
        tr = transport('{}'); tr['body_text'] = '{}'
        self.assertEqual(rt.accounting({}, tr, .17)[0], .17)

    def test_atomic_cap_rejects_without_send(self):
        with tempfile.TemporaryDirectory(dir=c.PRIVATE) as tmp:
            with patch.object(c, 'PRIVATE', Path(tmp)), patch.object(rt, 'load_config', return_value=Config('fixture')), patch.object(rt.DirectClient, 'send', side_effect=AssertionError('must not send')):
                con = rt.db(); con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)', ('old',1,'fixture',49.99,0,'')); con.commit(); con.close()
                self.assertEqual(rt.process(dict(request_id='new',arm='fixture',busy_bound_cny=.1), operating=50), 'budget_stop')
                self.assertEqual(rt.summary()['attempts'], 1)

    def test_frozen_arms_target_and_example_invariants(self):
        freeze = c.read(c.OUT / 'execution_freeze.json')
        for rel, checksum in freeze['files'].items():
            self.assertEqual(c.sha(c.ROOT / rel), checksum)
        jobs = c.lines(c.PRIVATE / 'jobs.jsonl')
        rows = {r['id']:r for r in c.lines(c.PRIVATE / 'sample.jsonl')}
        self.assertEqual(len(jobs), len({j['request_id'] for j in jobs}))
        self.assertFalse(set(freeze['example_development_patients']) & set(freeze['evaluation_patients']))
        for j in jobs:
            body = j['body']; r = rows[j['id']]
            payload = json.loads(body['messages'][1]['content'].split('## Input JSON:\n')[-1])
            self.assertEqual(payload, dict(text=r['claim'], reference=r['C48'] if j['arm']=='C' else r['published_reference']))
            self.assertNotIn('response_format', body)
            self.assertEqual(body['model'], c.MODEL)
            self.assertEqual(body['max_tokens'], 8192)
            self.assertTrue(body['enable_thinking'])
            self.assertEqual(body['reasoning_effort'], 'high')
            self.assertEqual(body['temperature'], 0)
        demos = c.read(c.PRIVATE / 'demonstrations.json')
        old = c.read(c.ROOT/'outputs/replays/090_demo_constructor_repair_validation/final/demonstrations.json')
        self.assertEqual(demos['P'], old['P90'])
        self.assertEqual(demos['F'], old['F4'])
        for p,q,f in zip(demos['P'],demos['Q'],demos['F']):
            for k in ['claim','proposition_id','sid','physician_label','ordinal']:
                self.assertEqual(p[k],q[k]); self.assertEqual(p[k],f[k])

if __name__ == '__main__':
    unittest.main()
