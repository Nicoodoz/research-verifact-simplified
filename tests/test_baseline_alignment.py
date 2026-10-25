"""010 same-Judge inputs and copied transport recovery, with fictional clients."""
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tasks/010_verifact_baseline_alignment'))
import alignment_common as a
from native_stage010 import StageRunner
from verifact_research.inference.siliconflow_pool import Account

def job(rid='one'):
    return dict(request_id=rid,kind='chat',body=dict(model=a.CHAT_MODEL,messages=[dict(role='user',content='fictional')],max_tokens=500))

def response(status=200):
    body=dict(model=a.CHAT_MODEL,choices=[dict(message=dict(content='{}'),finish_reason='stop')],usage=dict(prompt_tokens=500,completion_tokens=100,total_tokens=600))
    if status==402:
        body=dict(code=30001,message='Balance insufficient',data=None)
    return dict(http_status=status,body_text=json.dumps(body),outcome_unknown=False,headers={},started_utc='2026-09-15T12:00:00+00:00',ended_utc='2026-09-15T12:00:01+00:00')

class AlignmentTests(unittest.TestCase):
    def setUp(self):
        for target in ('socket.create_connection','socket.socket.connect','socket.socket.connect_ex'):
            guard=patch(target,side_effect=AssertionError('Network prohibited'))
            guard.start()
            self.addCleanup(guard.stop)

    def test_only_reference_changes_in_complete_judge_body(self):
        prompts=dict(common='definitions',structured='same checks')
        item=dict(text='Unchanged claim',human_gt='NEVER SEND',source='NEVER SEND')
        first=a.judge_body(item,'First reference',prompts)
        second=a.judge_body(item,'Second reference',prompts)
        self.assertEqual(json.loads(first['messages'][1]['content']),dict(proposition='Unchanged claim',reference='First reference'))
        self.assertNotIn('NEVER SEND',json.dumps(first))
        first['messages'][1]['content']=second['messages'][1]['content']
        self.assertEqual(first,second)

    def test_balance_recovery_and_resume_never_resend_received_body(self):
        calls=[]
        class Client:
            def send(self,account,j):
                calls.append((account.alias,j))
                return response(402 if account.alias=='empty' else 200)
        with tempfile.TemporaryDirectory() as tmp:
            args=('judge',[job()],[Account('empty','FICTIONAL_ONE'),Account('next','FICTIONAL_TWO')])
            run=StageRunner(*args,client=Client(),output=tmp)
            self.assertTrue(run.run(1,0)['complete'])
            self.assertTrue(StageRunner(*args,client=Client(),output=tmp).run(1,0)['complete'])
            self.assertEqual(len(calls),2)
            self.assertEqual(calls[0][1],calls[1][1])
            self.assertAlmostEqual(run.state['used_or_reserved_cny'],.0024)

    def test_total_40_cap_stops_before_call_and_inputs_cannot_change(self):
        class Client:
            def send(self,account,j):
                raise AssertionError('Not affordable, must not send')
        with tempfile.TemporaryDirectory() as tmp:
            huge=job();huge['body']['max_tokens']=10000000
            args=('judge',[huge],[Account('one','FICTIONAL')])
            r=StageRunner(*args,client=Client(),output=tmp).run(1,0)
            self.assertEqual(r['status_counts'],dict(pending=1))
            self.assertEqual(r['cap_cny'],40)
            huge['body']['max_tokens']=500
            with self.assertRaises(ValueError):
                StageRunner(*args,client=Client(),output=tmp).run(1,0)

    def test_terminal_service_failure_does_not_abandon_other_claims(self):
        counts={}
        class Client:
            def send(self,account,j):
                rid=j['request_id'];counts[rid]=counts.get(rid,0)+1
                return response(503 if rid=='one' else 200)
        with tempfile.TemporaryDirectory() as tmp:
            r=StageRunner('judge',[job(),job('two')],[Account('one','FICTIONAL')],client=Client(),output=tmp).run(1,0)
            self.assertEqual(r['status_counts'],dict(failed_service=1,received=1))
            self.assertEqual(counts,dict(one=3,two=1))

if __name__=='__main__':
    unittest.main()
