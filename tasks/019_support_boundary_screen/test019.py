"""Offline regression and fake-transport checks. No real API calls or credentials."""
import copy, json, math, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import common019 as c
import run019 as run
import analysis019 as a
from verifact_research.inference.siliconflow_pool import Account
from verifact_research.inference.aliyun import Config


def response(scores=None, finish='stop'):
    obj=dict(verdict='Supported',reason='Synthetic evidence.',checks=[])
    if scores is not None:obj['label_scores']=scores
    return dict(http_status=200,body_text=json.dumps(dict(model=c.MODEL,choices=[dict(finish_reason=finish,message=dict(content=json.dumps(obj)))],usage=dict(prompt_tokens=20,completion_tokens=10,total_tokens=30))),outcome_unknown=False)

class Test019(unittest.TestCase):
    def setUp(self): self.q=dict(zip(c.LABELS,[40,50,10]))
    def test_original_body_exact(self):
        self.assertEqual(c.body('a','b'),c.old.judge_body({'text':'a'},'b',c.read(c.PROMPTS),'v4_first'))
    def test_only_score_changes(self):
        b=c.body('a','b');s=c.body('a','b',True)
        self.assertEqual(b['messages'][1],s['messages'][1])
        for k in b:
            if k not in ('messages','response_format'):self.assertEqual(b[k],s[k])
    def test_whitelist(self): self.assertEqual(set(json.loads(c.body('a','b')['messages'][1]['content'])),{'proposition','reference'})
    def test_valid_scores(self):self.assertEqual(c.parse(response(self.q),True)['scores'],self.q)
    def test_scores_missing(self):self.assertEqual(c.parse(response(),True)['status'],'invalid')
    def test_scores_float_rejected(self):
        self.q['Supported']=40.;self.assertEqual(c.parse(response(self.q),True)['status'],'invalid')
    def test_scores_boolean_rejected(self):
        self.q['Supported']=True;self.assertEqual(c.parse(response(self.q),True)['status'],'invalid')
    def test_scores_sum_rejected(self):
        self.q['Supported']=41;self.assertEqual(c.parse(response(self.q),True)['status'],'invalid')
    def test_truncated_rejected(self):self.assertEqual(c.parse(response(self.q,'length'),True)['status'],'invalid')
    def test_duplicate_key_rejected(self):
        with self.assertRaises(ValueError):c.strict_json('{"x":1,"x":2}')
    def test_epsilon(self):self.assertEqual(c.decision(dict(zip(c.LABELS,[0,50,50])),4),'Not Supported')
    def test_tie(self):self.assertEqual(c.decision(dict(zip(c.LABELS,[50,50,0])),0),'Not Supported')
    def test_monotone(self):
        for s in range(0,101,5):
            for n in range(0,101-s,5):
                q=dict(zip(c.LABELS,[s,n,100-s-n])); pp=[c.decision(q,l) for l in c.GRID]
                if 'Supported' in pp:self.assertTrue(all(x=='Supported' for x in pp[pp.index('Supported'):]))
                self.assertLessEqual(len(set(x for x in pp if x!='Supported')),1)
    def test_rhw(self):
        rows=[dict(human_gt=t) for t in c.LABELS]
        r=a.rhw(rows,['Not Supported','Not Supported','Not Supported'],['Supported']*3)
        self.assertEqual((r['R'],r['H'],r['W'],r['net_correct'],r['added_false_s']),(1,1,1,0,2))
    def test_random_no_gt(self):
        rows=[dict(subject_id='a',author_type='llm',human_gt='Supported') for _ in range(10)]
        base=['Not Supported']*10;counts={('a','llm','Not Supported'):3}
        first=a.random_flip(rows,base,counts,13)
        for r in rows:r['human_gt']='Not Addressed'
        self.assertEqual(first,a.random_flip(rows,base,counts,13));self.assertEqual(first.count('Supported'),3)
    def test_budget(self):self.assertTrue(run.allowed_budget(79.9,.1));self.assertFalse(run.allowed_budget(79.9,.10000001))
    def test_unknown_cost_reserved(self):self.assertEqual(c.charge(c.body('a','b'),dict(http_status=0,body_text=''))[0],c.bound(c.body('a','b')))
    def test_balance_not_service(self):
        for status in (0,400,401,403,429,503):self.assertFalse(c.balance_exhausted(dict(http_status=status,body_text='{}')))
    def test_no_score_normalization(self):
        self.q['Supported']=-1;self.assertEqual(c.parse(response(self.q),True)['status'],'invalid')
    def test_repeat_ids_differ(self):
        h=c.fingerprint(c.body('a','b'));self.assertNotEqual('019:validation:r0:'+h,'019:validation:r1:'+h)
    def test_missing_strict(self):
        rows=[dict(proposition_id='p',subject_id='s',human_gt='Supported')]
        with self.assertRaises(ValueError):c.evaluate(rows,[],profile='none')
    def test_real_routing_simulated(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);prep=out/'probe/preparation';prep.mkdir(parents=True)
            j=dict(request_id='fake',body=c.body('a','b'),stage='probe',arm='B',repeat=0,proposition_id='fake')
            c.write_lines(prep/'jobs.jsonl',[j])
            calls=[]
            class SF:
                def __init__(self,**kwargs):pass
                def send(self,account,body):
                    calls.append(account.alias)
                    return dict(http_status=402,body_text='{"code":30001,"data":null}',outcome_unknown=False)
            class ALI:
                def __init__(self,*args,**kwargs):pass
                def send(self,body):calls.append('aliyun_main');return response()
            cfg=Config(api_key='FAKE_ALI',model=c.ALI_MODEL)
            auth=dict(accounts=['account_2','account_3'],Alibaba_endpoint=cfg.endpoint)
            with patch.object(c,'OUT',out),patch.object(c,'GLOBAL_ROUTE',out/'global.json'),patch.object(c,'check_manifest',return_value=auth),patch.object(c,'load_accounts',return_value=[Account('account_2','FAKE2'),Account('account_3','FAKE3')]),patch.object(c,'load_config',return_value=cfg),patch.object(c,'HttpClient',SF),patch.object(c,'AliyunClient',ALI):
                r=run.run('probe',workers=1);self.assertEqual(r['halt'],'pool_exhausted')
                r=run.run('probe',workers=1);self.assertTrue(r['complete'])
                run.run('probe',workers=1)
                self.assertEqual(calls,['account_2','account_3','aliyun_main'])
                state=c.read(out/'live_ledger.json');self.assertAlmostEqual(state['used_or_reserved_cny'],.00015)
                self.assertEqual(len(state['phases']['probe']['jobs']['fake']['receipts']),3)
                self.assertNotIn('FAKE_ALI',''.join(p.read_text() for p in out.rglob('*.json')))

if __name__=='__main__':unittest.main()
