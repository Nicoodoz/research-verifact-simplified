import json,unittest
import common028 as c
class Trace(unittest.TestCase):
    def setUp(self):
        self.text='The patient received oxygen.';self.ref='Hospital Admission Start: 2100-01-01\n1. Date: 2100-01-01, Note ID: 123 | Text: The patient received oxygen by mask.'
        self.job=dict(arm='trace',model_key='deepseek',body=c.body(self.text,self.ref,'trace'))
        self.obj=dict(claim_coverage='complete',requirements=[dict(claim_quote='received oxygen',requirement='Received oxygen',evidence_fact='Oxygen by mask',relation='supported',evidence=[dict(reference_id=1,quote='received oxygen by mask.')])],summary='Supported requirement')
    def tr(self,obj=None,raw=None):return dict(http_status=200,body_text=json.dumps(dict(model=c.MODEL,choices=[dict(message=dict(content=raw or json.dumps(obj or self.obj)),finish_reason='stop')],usage=dict(prompt_tokens=10,completion_tokens=20,total_tokens=30))))
    def test_supported_with_grounded_quotes(self):
        p=c.parse(self.tr(),self.job);self.assertTrue(p['keep']);self.assertTrue(p['fully_traceable']);a,b=p['rows'][0]['evidence'][0]['reference_spans'][0];self.assertEqual(self.ref[a:b],'received oxygen by mask.')
    def test_uncertain_or_unaddressed_rejects(self):
        for relation in ['uncertain','unaddressed','contradicted']:
            self.obj['requirements'][0]['relation']=relation;self.assertFalse(c.parse(self.tr(),self.job)['keep'])
    def test_wrong_reference_or_claim_quote_fail_closed(self):
        self.obj['requirements'][0]['evidence'][0]['reference_id']=123;p=c.parse(self.tr(),self.job);self.assertFalse(p['keep']);self.assertIn(p['status'],c.VALID)
        self.obj['requirements'][0]['evidence'][0]['reference_id']=1;self.obj['requirements'][0]['claim_quote']='oxygen all stay';self.assertFalse(c.parse(self.tr(),self.job)['keep'])
    def test_conflicting_relation_invalid(self):
        raw=json.dumps(self.obj).replace('"relation": "supported"','"relation": "supported", "relation": "contradicted"');self.assertEqual(c.parse(self.tr(raw=raw),self.job)['status'],'invalid_core_fields')
    def test_noncore_duplicate_does_not_block(self):
        raw=json.dumps(self.obj)[:-1]+',"summary":"other prose"}';p=c.parse(self.tr(raw=raw),self.job);self.assertTrue(p['keep']);self.assertEqual(p['status'],'valid_with_format_anomaly')
    def test_whitespace_only_quote_matching(self):
        self.assertEqual(c.matches('received oxygen','received\n oxygen'),[[0,16]]);self.assertFalse(c.matches('did not receive oxygen','received oxygen'))
    def test_body_fixed_input_and_generation(self):
        b=c.body(self.text,self.ref,'repeat');t=self.job['body'];self.assertEqual(b['messages'][1],t['messages'][1]);self.assertEqual(json.loads(b['messages'][1]['content']),dict(proposition=self.text,reference=self.ref))
        for k in ('temperature','max_tokens','enable_thinking','stream','n'):self.assertEqual(b[k],t[k])
        self.assertEqual(b['max_tokens'],4096)
    def test_no_missing_citation_acceptance(self):
        self.obj['requirements'][0]['evidence']=[];p=c.parse(self.tr(),self.job);self.assertFalse(p['keep']);self.assertTrue(p['relation_only_keep'])
if __name__=='__main__':unittest.main()
