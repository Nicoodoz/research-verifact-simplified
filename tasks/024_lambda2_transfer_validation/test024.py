import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import common024 as c
class Integrity(unittest.TestCase):
    def test_lambda_is_historical(self):
        for s in range(101):
            q={'Supported':s,'Not Supported':100-s,'Not Addressed':0}
            for lam in (0,2):self.assertEqual(c.old.decision(q,lam),c.old.prior.decision(q,lam))
        with self.assertRaises(ValueError):c.old.decision(q,1.5)
    def test_body_whitelist_and_setting(self):
        for scored in (False,True):
            b=c.old.body('test claim','test reference',scored)
            self.assertEqual(json.loads(b['messages'][1]['content']),{'proposition':'test claim','reference':'test reference'})
            self.assertEqual(b['max_tokens'],2048);self.assertFalse(b['enable_thinking'])
    def test_cost_and_unknown(self):
        j={'model_key':'qwen','body':c.old.body('x','y')}
        tr={'body_text':json.dumps({'usage':{'prompt_tokens':1000,'completion_tokens':100,'total_tokens':1100}})}
        self.assertAlmostEqual(c.charge(j,tr)[0],.0042)
        self.assertEqual(c.charge(j,{'body_text':''})[0],c.bound(j))
    def test_terminal_binding_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td,patch.object(c,'OUT',Path(td)):
            j={'request_id':'x','model_key':'deepseek','arm':'B','body':dict(c.old.body('a','b'),model=c.MODELS['deepseek'])}
            d=Path(td)/'attempts/x_01';p=d/'request.json'
            r=dict(request_id='x',body=j['body'],body_sha256=c.fingerprint(j['body']),reservation_cny=c.bound(j))
            c.put(p,r)
            a,t=c.load_attempts([j]);self.assertEqual(len(t),0);self.assertEqual(a[0]['charge_cny'],c.bound(j))
            with self.assertRaises(FileExistsError):c.put(p,r)
            native=dict(model=c.MODELS['deepseek'],choices=[dict(finish_reason='stop',message=dict(content=json.dumps(dict(verdict='Supported',reason='test',checks=[]))))],usage=dict(prompt_tokens=100,completion_tokens=10))
            c.put(d/'receipt.json',dict(request_sha256=c.file_hash(p),transport=dict(http_status=200,body_text=json.dumps(native))))
            a,t=c.load_attempts([j]);self.assertEqual(t['x']['status'],'success');self.assertLess(a[0]['charge_cny'],c.bound(j))
            d2=Path(td)/'attempts/x_02';c.put(d2/'request.json',r)
            c.put(d2/'receipt.json',dict(request_sha256=c.file_hash(d2/'request.json'),transport=dict(http_status=200,body_text=json.dumps(native))))
            with self.assertRaises(ValueError):c.load_attempts([j])
    def test_invalid_score_terminal(self):
        answer=dict(verdict='Supported',reason='x',checks=[],label_scores={'Supported':50,'Not Supported':10,'Not Addressed':10})
        n=dict(choices=[dict(finish_reason='stop',message=dict(content=json.dumps(answer)))])
        self.assertEqual(c.old.prior.parse(dict(http_status=200,body_text=json.dumps(n)),True)['status'],'invalid')
if __name__=='__main__':unittest.main()
