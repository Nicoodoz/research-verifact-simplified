import unittest,tempfile
from unittest.mock import patch
from common import *
import provider,runner,remote_server
sys.path.insert(0,str(ROOT/'tasks/085_r1_70b_model_swap'))
from parse_r1 import ParserProfile,parse

class FakeTransport:
    timeout=1
    def __init__(self,statuses):self.statuses=iter(statuses);self.calls=0
    def request(self,path,body=None):
        self.calls+=1;s=next(self.statuses)
        return dict(http_status=s,raw=canonical(dict(model=MODEL,choices=[dict(message=dict(content='not valid verdict',reasoning_content='synthetic'),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=3,total_tokens=13))).encode(),started_utc=now(),ended_utc=now(),elapsed_seconds=.001,outcome_unknown=s==0)
class Tests(unittest.TestCase):
    def test_loopback_no_credentials(self):
        self.assertEqual(provider.base_url('http://127.0.0.1:8000/v1'),'http://127.0.0.1:8000/v1')
        for url in ('https://example.com/v1','http://user:secret@localhost:8000/v1','http://localhost:8000/v1?token=abc'):
            with self.assertRaises(ValueError):provider.base_url(url)
    def test_payload_semantics(self):
        neutral=lines(OLD/'neutral_jobs.jsonl')
        for x in neutral:
            b=body(x);self.assertEqual(b['messages'][0]['content'],x['instruction_semantic_content']);self.assertEqual(json.loads(b['messages'][1]['content']),dict(proposition=x['claim'],reference=x['reference']))
            self.assertEqual(set(b),{'model','messages','temperature','top_p','max_tokens','stream'})
            self.assertEqual((b['temperature'],b['top_p'],b['max_tokens']),(0,1,8192))
    def test_identity_content_not_name(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'config.json';p.write_bytes(b'actual')
            with self.assertRaises(ValueError):remote_server.verify_files(d,{'config.json':dict(size=6,sha256=digest(b'wrong!'))})
            self.assertEqual(remote_server.verify_files(d,{'config.json':dict(size=6,sha256=digest(b'actual'))})[0]['actual'],digest(b'actual'))
    def test_remote_command(self):
        lock=read(TASK/'identity_lock.json');c=remote_server.command('/cache/model','/cache/tokenizer',lock)
        for flag,value in (('--max-model-len','20000'),('--max-num-seqs','4'),('--tensor-parallel-size','1'),('--reasoning-parser','deepseek_r1'),('--generation-config','vllm')):self.assertEqual(c[c.index(flag)+1],value)
        self.assertNotIn('docker',c);self.assertIn('--enable-reasoning',c)
    def test_manifest_validates_pinned_files_and_actual_command(self):
        lock=read(TASK/'identity_lock.json');cmd=remote_server.command('/data/model','/data/tokenizer',lock)
        def file_rows(files):
            return [dict(name=n,algorithm='sha256' if v.get('sha256') else 'git_blob',expected=v.get('sha256') or v['git_blob'],actual=v.get('sha256') or v['git_blob']) for n,v in files.items()]
        m=dict(status='VERIFIED_FILES_BEFORE_SERVER_START',versions={'vllm':'0.9.2'},environment={'VLLM_USE_V1':'1'},gpu=['SYNTHETIC-A800-NOT-REAL'],server_command=cmd,
            model=dict(repo=MODEL,resolved_revision=lock['model']['revision'],local_path='/data/model',files=file_rows(remote_server.model_files(lock)),quantization=lock['model']['metadata']['config.json']['content']['quantization_config']),
            tokenizer=dict(repo=TOKENIZER,resolved_revision=lock['tokenizer']['revision'],local_path='/data/tokenizer',files=file_rows(lock['official_tokenizer_files']),chat_template_sha256=lock['chat_template_sha256']))
        o=dict(status='SERVICE_READY_OBSERVED',version={'version':'0.9.2'},actual_process_command=cmd,models={'data':[dict(id=MODEL,max_model_len=20000)]})
        self.assertTrue(provider.validate_manifest(m,o,lock))
        m['model']['resolved_revision']='0'*40
        with self.assertRaises(ValueError):provider.validate_manifest(m,o,lock)
    def test_success_invalid_not_repeated_and_stageB_reused(self):
        j=freeze_job(dict(id='synthetic',sid='none',arm='B',claim='x',reference='y',instruction_semantic_content='z'))
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'OUT',Path(d)),patch.object(runner,'ROOT',Path(d)):
            tr=FakeTransport([200]);runner.invoke(j,'B',tr);runner.invoke(j,'formal',tr);self.assertEqual(tr.calls,1)
            self.assertEqual(len(runner.state()[0]),1)
    def test_retry_finite_unknown_retained(self):
        j=freeze_job(dict(id='synthetic',sid='none',arm='B',claim='x',reference='y',instruction_semantic_content='z'))
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'OUT',Path(d)),patch.object(runner,'ROOT',Path(d)):
            tr=FakeTransport([0,503,200]);runner.invoke(j,'A',tr,sleep=lambda _:None)
            rows,success,counts=runner.state();self.assertEqual(tr.calls,3);self.assertEqual(len(rows),3);self.assertTrue(rows[0]['receipt']['outcome_unknown'])
        with tempfile.TemporaryDirectory() as d,patch.object(runner,'OUT',Path(d)),patch.object(runner,'ROOT',Path(d)):
            tr=FakeTransport([503,503,503])
            with self.assertRaises(RuntimeError):runner.invoke(j,'A',tr,sleep=lambda _:None)
            self.assertEqual(tr.calls,3)
    def test_missing_formal_approval(self):
        from argparse import Namespace
        with self.assertRaises(PermissionError):runner.formal([],None,Namespace(allow_formal=False,approval_note=None,max_runtime_hours=None))
    def test_no_guess_from_reasoning(self):
        p=ParserProfile(content_path=['choices',0,'message','content'],reasoning_path=['choices',0,'message','reasoning_content'],finish_path=['choices',0,'finish_reason'])
        e=dict(choices=[dict(message=dict(content='No final JSON',reasoning_content='Supported'),finish_reason='stop')]);self.assertFalse(parse(e,p)['valid'])
        e['choices'][0]['message']['content']='{"verdict":"Not Addressed"}';z=parse(e,p);self.assertTrue(z['valid']);self.assertIsNone(z['label_scores'])
        e['choices'][0]['finish_reason']='length';self.assertFalse(parse(e,p)['valid'])
    def test_GPU_ledger_no_invented_price(self):
        import runtime_ledger as ledger
        with tempfile.TemporaryDirectory() as d,patch.object(ledger,'OUT',Path(d)):
            self.assertIsNone(ledger.summarize()['gpu_cost_cny'])
            ledger.event('instance_start','2026-09-26T10:00:00+00:00',3);ledger.event('instance_end','2026-09-26T12:00:00+00:00')
            self.assertEqual(ledger.summarize()['gpu_cost_cny'],6)
    def test_preflight_selection_unchanged(self):
        chosen=runner.selected([freeze_job(j) for j in lines(OLD/'neutral_jobs.jsonl')]);self.assertEqual([x[0] for x in chosen],['short_B','median_F4','longest_F4']);self.assertEqual(len({x[1]['request_id'] for x in chosen}),3)
if __name__=='__main__':unittest.main()
