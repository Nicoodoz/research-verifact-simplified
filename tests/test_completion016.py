"""Cross-provider continuation guards, with synthetic paid transports only."""
from pathlib import Path
from contextlib import ExitStack,redirect_stdout
from unittest.mock import patch
from types import SimpleNamespace
import io
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/016_disagreement_triggered_review_validation'))
import common016 as c
import complete016 as run
from completion_io016 import collect,answers,OUT,ORIGINAL,ALI_MODEL

class CompletionTests(unittest.TestCase):
    def test_473_missing_only_and_prior_probe_reused(self):
        values,attempts,total=collect(False);a,_=answers(values)
        self.assertEqual(sum(k[1]=='qwen' for k in a),128)
        self.assertAlmostEqual(total,11.82850223,places=8)
        jobs=c.jsonlines(OUT/'base/jobs.jsonl');self.assertEqual(len(jobs),473)
        old={(j['proposition_id'],j['role']):j for j in c.jsonlines(ORIGINAL/'stage1/base_preparation_001/jobs.jsonl')}
        for j in jobs:
            key=(j['proposition_id'],j['role']);self.assertNotIn(key,a)
            self.assertEqual(j['body']['model'],ALI_MODEL)
            self.assertEqual(dict(j['body'],model=c.QWEN),old[key]['body'])

    def test_durable_budget_no_success_resend_and_error_pause(self):
        for http in (200,0):
            with self.subTest(http=http),tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
                out=Path(temp);(out/'base').mkdir();(out/'live').mkdir()
                job=dict(request_id='synthetic',kind='chat',role='qwen',proposition_id='fake',body=dict(model=ALI_MODEL))
                c.write_lines(out/'base/jobs.jsonl',[job]);c.write_json(out/'authority.json',dict(execution_sha256={}))
                c.write_json(out/'protocol_amendment.json',dict(Alibaba_endpoint='synthetic'))
                c.write_json(out/'live/ledger.json',dict(carry_cny=11.8,used_or_reserved_cny=11.8,exhausted_accounts=[],phases={}))
                calls=[]
                class FakeAli:
                    def __init__(self,config):pass
                    def send(self,body):
                        ledger=c.read(out/'live/ledger.json')
                        self_outer.assertAlmostEqual(ledger['used_or_reserved_cny'],11.9)
                        self_outer.assertEqual(ledger['phases']['base']['jobs']['synthetic']['status'],'in_flight')
                        calls.append(body)
                        return dict(http_status=http,body_text='{}',started_utc=c.now(),ended_utc=c.now(),outcome_unknown=http==0)
                self_outer=self
                stack.enter_context(patch.object(run,'OUT',out));stack.enter_context(patch.object(run,'forecast',return_value=[job]))
                stack.enter_context(patch.object(run,'collect',return_value=({},[],11.8)));stack.enter_context(patch.object(run,'answers',return_value=({},[])))
                stack.enter_context(patch.object(c,'check_manifest'));stack.enter_context(patch.object(run,'bound',return_value=.1))
                stack.enter_context(patch.object(run,'charge',return_value=(.02 if http==200 else .1,'synthetic')))
                stack.enter_context(patch.object(run,'load_config',return_value=SimpleNamespace(endpoint='synthetic',model=ALI_MODEL,api_key='fake-key')))
                stack.enter_context(patch.object(c,'load_accounts',return_value=[SimpleNamespace(alias='account_2',key='fake-other-key')]))
                stack.enter_context(patch.object(run,'AliyunClient',FakeAli));stack.enter_context(patch.object(c.old14,'normalize',return_value=dict(status='success')))
                with redirect_stdout(io.StringIO()):run.send('base',8)
                self.assertEqual(len(calls),1)
                l=c.read(out/'live/ledger.json');self.assertAlmostEqual(l['used_or_reserved_cny'],11.82 if http==200 else 11.9)
                self.assertEqual(l['phases']['base']['jobs']['synthetic']['status'],'received' if http==200 else 'retry')
                if http==200:
                    with redirect_stdout(io.StringIO()):run.send('base',8)
                    self.assertEqual(len(calls),1)

if __name__=='__main__':unittest.main()
