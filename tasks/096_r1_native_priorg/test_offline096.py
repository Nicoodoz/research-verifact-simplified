"""Offline behavior checks; no endpoints, no real inference or rent."""
import unittest,tempfile,datetime,json,socket
from pathlib import Path
from unittest.mock import patch
import common096 as c
import runner096 as r
from calibration096 import decode
from parse_r1 import ParserProfile,parse

class Offline(unittest.TestCase):
    def cfg(self):
        now=datetime.datetime.now(datetime.timezone.utc)
        return dict(gpu_billing_start=(now-datetime.timedelta(minutes=10)).isoformat(),stop_sending_at=(now+datetime.timedelta(hours=5)).isoformat(),gpu_hourly_cny=2,gpu_cap_cny=30,timeout_seconds=900,shutdown_margin_seconds=120,client_concurrency=2)
    def test_no_service_ready_no_network(self):
        with patch.object(socket.socket,'connect',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(AssertionError,'WAIT_FOR_USER_SERVICE_READY'):r.validate_runtime(c.TASK/'runtime.template.json')
    def test_shared_wall_budget_not_sum_of_request_times(self):
        cfg=self.cfg();a=r.budget_check(cfg);self.assertAlmostEqual(a['inflight_wall_reserve_cny'],2*1020/3600)
        cfg['gpu_cap_cny']=.5
        with self.assertRaisesRegex(RuntimeError,'STOP_NEW_SENDS'):r.budget_check(cfg)
    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError):r.aware('2026-09-28T10:00:00')
    def test_deadline_stops_even_budget_remains(self):
        cfg=self.cfg();cfg['stop_sending_at']=cfg['gpu_billing_start']
        with self.assertRaises(RuntimeError):r.budget_check(cfg)
    def test_http200_invalid_body_is_never_reissued(self):
        with tempfile.TemporaryDirectory(prefix='verifact096_test_') as tmp,patch.object(c,'PRIVATE',Path(tmp)),patch.object(r,'request',return_value=(b'{}',dict(http_status=200,outcome_unknown=False,elapsed_seconds=.01))) as send:
            body=dict(model=c.MODEL);j=dict(id='synthetic',sid='synthetic',stage='technical',body=body,body_sha256=c.digest(body),request_id='synthetic-invalid-200')
            a,_=r.invoke_once(j,self.cfg());b,_=r.invoke_once(j,self.cfg());self.assertEqual(a,b);self.assertEqual(send.call_count,1)
    def test_unknown_attempt_does_not_blindly_repeat(self):
        with tempfile.TemporaryDirectory(prefix='verifact096_test_') as tmp,patch.object(c,'PRIVATE',Path(tmp)),patch.object(r,'server_idle',return_value=False),patch.object(r,'request') as send:
            j=dict(request_id='synthetic-unknown',body_sha256='a');folder=Path(tmp)/'attempts'/j['request_id']/'1';c.put(folder/'request.json',dict(body_sha256='a'))
            with self.assertRaisesRegex(RuntimeError,'UNRESOLVED_PRIOR_INFLIGHT'):r.run_jobs([j],self.cfg())
            send.assert_not_called();self.assertFalse((Path(tmp)/'run.lock').exists())
    def test_decoder_original_tie_order(self):
        self.assertEqual(decode({'Supported':50,'Not Supported':50,'Not Addressed':0}),'Not Supported')
        self.assertEqual(decode({'Supported':0,'Not Supported':50,'Not Addressed':50}),'Not Supported')
    def test_raw_parser_does_not_invent_scores(self):
        profile=ParserProfile(content_path=['choices',0,'message','content'],finish_path=['choices',0,'finish_reason'])
        n=dict(choices=[dict(message=dict(content='<think>synthetic trace</think>{"verdict":"Supported"}'),finish_reason='stop')]);p=parse(n,profile)
        self.assertTrue(p['valid']);self.assertIsNone(p['label_scores']);self.assertEqual(p['reasoning'],'synthetic trace')
        n['choices'][0]['finish_reason']='length';self.assertFalse(parse(n,profile)['valid'])
    def test_metered_crash_after_success_receipt_reconciles_without_resend(self):
        import sqlite3
        from metered_bridge096 import reconcile_api
        with tempfile.TemporaryDirectory(prefix='verifact096_test_') as tmp,patch.object(c,'PRIVATE',Path(tmp)):
            folder=Path(tmp)/'metered_attempts'/'synthetic-api'/'1';j=dict(request_id='synthetic-api',bound_cny=.1)
            c.put(folder/'request.json',dict(job=j,attempt=1));c.put(folder/'receipt.json',dict(request_sha256=c.sha(folder/'request.json'),transport=dict(http_status=200)))
            db=sqlite3.connect(':memory:');db.execute('CREATE TABLE attempts(rid TEXT,n INT,charge REAL,status INT,path TEXT,PRIMARY KEY(rid,n))');db.execute('INSERT INTO attempts VALUES(?,?,?,?,?)',('synthetic-api',1,.1,None,'synthetic'))
            reconcile_api(db,lambda job,tr:.02);self.assertEqual(db.execute('SELECT charge,status FROM attempts').fetchone(),(.02,200));db.close()
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('All096 tests offline')):unittest.main()
