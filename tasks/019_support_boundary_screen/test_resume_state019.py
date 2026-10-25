"""Simulation of interruption recovery and terminal malformed responses."""
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import io
import tempfile
import unittest
import common019 as c
import run019 as run
from test019 import response
from verifact_research.inference.siliconflow_pool import Account
from verifact_research.inference.aliyun import Config

class ResumeStateTests(unittest.TestCase):
    def scenario(self, has_receipt, malformed=False):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            out=Path(directory); prep=out/'probe/preparation'; prep.mkdir(parents=True)
            (out/'probe/live').mkdir()
            job=dict(request_id='fake',body=c.body('a','b'),stage='probe',arm='B',repeat=0,proposition_id='fake')
            c.write_lines(prep/'jobs.jsonl',[job]); reserve=c.bound(job['body'])
            progress=dict(status='in_flight',attempts=1,transient=0,unknown=0,receipts=[],reserved_cny=reserve)
            state=dict(cap_cny=80,used_or_reserved_cny=reserve,provider='siliconflow',exhausted_accounts=[],phases={'probe':{'jobs':{'fake':progress}}})
            c.write_json(out/'live_ledger.json',state)
            if has_receipt:
                rec=dict(request_id='fake',job_sha256=c.fingerprint(job),actual_body=job['body'],actual_body_sha256=c.fingerprint(job['body']),attempt=1,provider='siliconflow',account='account_2',transport=response(finish='length' if malformed else 'stop'))
                c.write_json(out/'probe/live/receipt_000001_01.json',rec)
            calls=[]
            class Client:
                def __init__(self,*args,**kwargs): pass
                def send(self,*args):
                    calls.append(1)
                    return response()
            cfg=Config(api_key='FAKE_ALI',model=c.ALI_MODEL)
            replacements=dict(OUT=out,GLOBAL_ROUTE=out/'global.json')
            for key,value in replacements.items(): stack.enter_context(patch.object(c,key,value))
            stack.enter_context(patch.object(c,'check_manifest',return_value=dict(accounts=['account_2'],Alibaba_endpoint=cfg.endpoint)))
            stack.enter_context(patch.object(c,'load_accounts',return_value=[Account('account_2','FAKE2')]))
            stack.enter_context(patch.object(c,'load_config',return_value=cfg))
            stack.enter_context(patch.object(c,'HttpClient',Client))
            stack.enter_context(patch.object(c,'AliyunClient',Client))
            clock=[1000]
            def tick():
                clock[0]+=100
                return clock[0]
            stack.enter_context(patch.object(run.time,'time',tick))
            stack.enter_context(redirect_stdout(io.StringIO()))
            result=run.run('probe',workers=1)
            state=c.read(out/'live_ledger.json'); p=state['phases']['probe']['jobs']['fake']
            self.assertTrue(result['complete'])
            self.assertEqual(len(calls),0 if has_receipt else 1)
            self.assertEqual(p['attempts'],1 if has_receipt else 2)
            self.assertAlmostEqual(state['used_or_reserved_cny'],.00015+(0 if has_receipt else reserve))
            self.assertEqual(len(p.get('unreceipted_attempts',[])),0 if has_receipt else 1)
            if malformed: self.assertEqual(p['parse_status'],'invalid')

    def test_receipt_reconciled_without_resending(self):
        self.scenario(True)

    def test_no_receipt_keeps_unknown_cost(self):
        self.scenario(False)

    def test_malformed_http200_is_not_resent(self):
        self.scenario(True, malformed=True)

if __name__=='__main__':
    unittest.main()
