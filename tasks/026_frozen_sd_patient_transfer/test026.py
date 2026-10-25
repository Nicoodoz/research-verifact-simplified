import copy,json,unittest
import common026 as c
class FrozenGate(unittest.TestCase):
    def test_features_equal025(self):
        rows=[r for r in c.lines(c.ROOT/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl') if r['group'] in ('024_D','024_Q')]
        q={r['proposition_id']:r for r in rows if r['group']=='024_Q'}
        for r in rows:
            if r['group']!='024_D':continue
            f=c.features(r['scores'],q[r['proposition_id']]['scores'])
            self.assertEqual(set(f),set(c.risk.METHODS['SD']))
            for k in f:self.assertEqual(f[k],r['features'][k])
    def test_noncore_conflict_does_not_block(self):
        text='{"verdict":"Supported","reason":"a","reason":"b","label_scores":{"Supported":70,"Not Supported":20,"Not Addressed":10}}'
        t=dict(http_status=200,body_text=json.dumps(dict(model=c.MODELS['deepseek'],choices=[dict(finish_reason='stop',message=dict(content=text))])))
        before=copy.deepcopy(t);r=c.parse(t,True);self.assertIn(r['status'],c.VALID);self.assertEqual(before,t)
    def test_body_matches024_except_claim_reference(self):
        body=c.api.old.body('claim','reference',True)
        self.assertEqual(json.loads(body['messages'][1]['content']),{'proposition':'claim','reference':'reference'})
        self.assertFalse(body['enable_thinking']);self.assertEqual(body['max_tokens'],2048)
    def test_core_conflict_is_invalid(self):
        s='{"verdict":"Supported","verdict":"Not Supported"}'
        t=dict(http_status=200,body_text=json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content=s))])))
        self.assertEqual(c.parse(t,False)['status'],'invalid_core_fields')
if __name__=='__main__':unittest.main()
