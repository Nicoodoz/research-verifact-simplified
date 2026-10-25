"""Offline unit and simulated routing checks. Fake fixtures incur no API cost."""
import json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import common020 as c
import run020 as run
from verifact_research.inference.siliconflow_pool import Account
from verifact_research.inference.aliyun import Config
class Tests(unittest.TestCase):
    def test_original_body(self):
        self.assertEqual(c.body('a','b'),c.prior.old.judge_body({'text':'a'},'b',c.prior.read(c.prior.PROMPTS),'v4_first'))
    def test_score_body(self):self.assertEqual(c.body('a','b',True),c.prior.body('a','b',True))
    def test_whitelist(self):self.assertEqual(json.loads(c.body('a','b',True)['messages'][1]['content']),{'proposition':'a','reference':'b'})
    def test_decode_all_integer_scores(self):
        for s in range(101):
            for n in range(101-s):
                q=dict(zip(c.LABELS,[s,n,100-s-n]))
                for lam in (0,2):
                    z=max(s/100,1e-6)*math.exp(lam);nn=max(n/100,1e-6);aa=max((100-s-n)/100,1e-6)
                    y='Supported' if z>max(nn,aa) else 'Not Supported' if nn>=aa else 'Not Addressed'
                    self.assertEqual(c.decision(q,lam),y)
    def test_no_new_lambda(self):
        with self.assertRaises(ValueError):c.decision(dict(zip(c.LABELS,[30,60,10])),1.5)
    def test_patient_isolation(self):
        ids=c.patient_ids('new10');g=c.read(c.ROOT/'outputs/003_error_analysis/patient_groups.json')['groups']
        self.assertEqual(len(ids),10);self.assertFalse(set(ids)&set(g['reserved_test']))
        self.assertFalse(set(ids)&set(c.baseline.patient_order()[:30]))
    def test_budget(self):self.assertTrue(run.allowed_budget(79.9,.1));self.assertFalse(run.allowed_budget(79.9,.100001))
    def test_missing_strict(self):
        with self.assertRaises(ValueError):c.evaluate([dict(proposition_id='a',subject_id='a',human_gt='Supported')],[],profile='none')
    def test_native_validation(self):
        j={'kind':'rerank','body':{'model':c.baseline.RERANK_MODEL,'documents':['x','y']}}
        tr={'http_status':200,'body_text':json.dumps({'results':[{'index':0,'relevance_score':.3}]})}
        self.assertEqual(c.parse(j,tr)['status'],'invalid')
    def test_invalid_scores_no_repair(self):
        j={'kind':'chat','arm':'S'}
        o={'verdict':'Supported','reason':'fixture','checks':[],'label_scores':dict(zip(c.LABELS,[40,40,10]))}
        tr={'http_status':200,'body_text':json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(o)}}]})}
        self.assertEqual(c.parse(j,tr)['status'],'invalid')
    def test_service_is_not_balance(self):
        for s in (0,429,503,401):self.assertFalse(c.balance_exhausted({'http_status':s,'body_text':'{}'}))
    def test_unknown_preserved(self):
        j={'kind':'chat','body':c.body('a','b')}
        self.assertEqual(c.charge(j,{'http_status':0,'body_text':''})[0],c.bound(j))
    def test_fake_pool_then_single_aliyun(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);prep=out/'new10/base_preparation_001';prep.mkdir(parents=True)
            j=dict(request_id='fixture',kind='chat',body=c.body('a','b'),arm='B',repeat=0,proposition_id='fake')
            c.write_lines(prep/'jobs.jsonl',[j]);calls=[]
            class SF:
                def send(self,account,job):
                    calls.append(account.alias)
                    return dict(http_status=402,body_text='{"code":30001,"data":null}',outcome_unknown=False)
            class Ali:
                def __init__(self,*a,**kw):pass
                def send(self,body):
                    calls.append('aliyun_main');obj={'verdict':'Supported','reason':'fixture','checks':[]}
                    return dict(http_status=200,body_text=json.dumps({'choices':[{'finish_reason':'stop','message':{'content':json.dumps(obj)}}],'usage':{'prompt_tokens':20,'completion_tokens':10,'total_tokens':30}}))
            cfg=Config(api_key='FAKE_ALI',model=c.ALI_MODEL)
            auth=dict(accounts=['account_2','account_3'],Alibaba_endpoint=cfg.endpoint)
            with patch.object(c,'ROOT',out),patch.object(c,'OUT',out),patch.object(c,'GLOBAL_ROUTE',out/'routing.json'),patch.object(c,'check_manifest',return_value=auth),patch.object(c,'load_accounts',return_value=[Account('account_2','FAKE2'),Account('account_3','FAKE3')]),patch.object(c,'load_config',return_value=cfg),patch.object(c.NATIVE,'HttpClient',SF),patch.object(c,'AliyunClient',Ali):
                result=run.run('new10_judge',workers=1)
                self.assertEqual(result['halt'],'pool_exhausted')
                self.assertTrue(run.run('new10_judge',workers=1)['complete'])
                run.run('new10_judge',workers=1)
                self.assertEqual(calls,['account_2','account_3','aliyun_main'])
                self.assertAlmostEqual(c.read(out/'live_ledger.json')['used_or_reserved_cny'],.00015)
                self.assertNotIn('FAKE_ALI',''.join(p.read_text(encoding='utf-8') for p in out.rglob('*.json')))
if __name__=='__main__':unittest.main()
