"""Offline money and recovery invariants; no network or clinical cases."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import api104 as a

def transport(start='2026-10-27T12:00:00+00:00',end='2026-10-27T12:00:10+00:00',model=a.MODEL):
    return dict(http_status=200,outcome_unknown=False,started_utc=start,ended_utc=end,
                body_text=json.dumps(dict(model=model,usage=dict(prompt_tokens=1000,completion_tokens=100,prompt_tokens_details=dict(cached_tokens=800)))))

class BudgetTests(unittest.TestCase):
    def test_no_cache_budget(self):
        amount,basis,usage=a.account(transport(),100_000_000)
        self.assertEqual(amount,3_900_000)
        self.assertEqual(basis,'verified_usage_no_cache')
        self.assertLess(usage['cost_with_official_cache_cny'],usage['cost_no_cache_cny'])

    def test_idle_and_boundary(self):
        idle=transport('2026-10-27T15:00:00+00:00','2026-10-27T15:00:10+00:00')
        self.assertEqual(a.account(idle,100_000_000)[0],1_950_000)
        crossing=transport('2026-10-27T13:59:59+00:00','2026-10-27T14:00:01+00:00')
        self.assertEqual(a.account(crossing,100_000_000)[0],3_900_000)

    def test_unknown_and_model_mismatch_keep_reserve(self):
        for value in (None,dict(http_status=0,outcome_unknown=True),transport(model='different')):
            self.assertEqual(a.account(value,987654321)[:2],(987654321,'unknown_or_unverified_reserve'))

    def test_unexpected_cost_is_not_hidden(self):
        value,basis,_=a.account(transport(),1)
        self.assertEqual(value,3_900_000)
        self.assertEqual(basis,'verified_usage_exceeded_reservation')

    def test_reservation_covers_output_and_bytes(self):
        request=a.body(dict(claim='Synthetic assertion',reference='Synthetic source'),dict(evidence=[],relation='Synthetic test',verdict='Not Addressed'))
        self.assertGreater(a.reserve_nano(request),8192*9000)
        self.assertEqual(request['model'],a.MODEL)

    def test_existing_http200_never_resends(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(a.c,'PRIVATE',Path(folder)):
            con=a.db();con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',('test',1,'quality',1,200,'verified_usage_no_cache','not-used'));con.commit();con.close()
            with patch.object(a,'load_config',return_value=a.Config('x'*32,a.ENDPOINT,a.MODEL)),patch.object(a.DirectClient,'send',side_effect=AssertionError('Must not send')):
                self.assertEqual(a.process(dict(request_id='test',phase='quality',body={})), 'already_answered')

    def test_hard_cap_counts_prior_unknown(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(a.c,'PRIVATE',Path(folder)):
            con=a.db();con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',('prior',1,'quality',a.OPERATING_NANO,0,'unknown_or_unverified_reserve','not-used'));con.commit();con.close()
            request=a.body(dict(claim='Synthetic assertion',reference='Synthetic source'),dict(evidence=[],relation='Synthetic test',verdict='Not Addressed'))
            with patch.object(a,'load_config',return_value=a.Config('x'*32,a.ENDPOINT,a.MODEL)),patch.object(a.DirectClient,'send',side_effect=AssertionError('Must not send')):
                self.assertEqual(a.process(dict(request_id='next',phase='quality',body=request)), 'budget_stop')
            self.assertEqual(a.summary()['attempts'],1)

    def test_bad_answer_not_a_new_label(self):
        response={'choices':[{'finish_reason':'stop','message':{'content':'{"verdict":"Supported"}'}}]}
        self.assertFalse(a.parse(response)['valid'])
        response['choices'][0]['finish_reason']='length'
        self.assertFalse(a.parse(response)['valid'])

    def test_quality_schema_and_duplicate_keys(self):
        value=dict(recommendation='retain',checks={k:True for k in ['quotes_faithful','subject_event_time','qualifiers_preserved','reference_explains_verdict','no_label_rationalization']},critical_issues=[],brief_assessment='Synthetic quality check')
        response={'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}
        self.assertTrue(a.parse(response)['valid'])
        response['choices'][0]['message']['content']='{"recommendation":"retain",'+json.dumps(value)[1:]
        self.assertFalse(a.parse(response)['valid'])

if __name__=='__main__':unittest.main()
