"""Contract and budget safety tests; synthetic strings only, no API."""
import json,unittest
import common101 as c,prompts101 as p,runtime101 as rt
class Contracts(unittest.TestCase):
 def tr(self,obj,finish='stop'):
  return dict(http_status=200,body_text=json.dumps(dict(model=c.MODEL,choices=[dict(message=dict(content=json.dumps(obj)),finish_reason=finish)])))
 def test_supported_rejected(self):
  self.assertFalse(p.parse(self.tr(dict(verdict='Supported',reason='x')),'nsna_plain','x')['valid'])
 def test_no_na_from_bad_format(self):
  self.assertIsNone(p.parse(self.tr(dict(verdict='NA',reason='x')),'nsna_plain','x')['verdict'])
 def test_quotes(self):
  obj=dict(asserted_fact='x',correspondence='x',verdict='Not Supported',evidence_quotes=['Refused the test.'])
  self.assertTrue(p.parse(self.tr(obj),'nsna_review','Today: Refused the test.')['valid'])
  self.assertFalse(p.parse(self.tr(obj),'nsna_review','Today: Completed the test.')['valid'])
 def test_na_empty_quotes(self):
  self.assertTrue(p.parse(self.tr(dict(asserted_fact='x',correspondence='not found',verdict='Not Addressed',evidence_quotes=[])),'nsna_review','x')['valid'])
 def test_whitespace_only(self):
  self.assertIsNotNone(p.locate('a\n b c','a b'))
  self.assertIsNone(p.locate('a  4 b','a 5 b'))
  self.assertIsNone(p.locate('a\n b a\n b','a b'))
 def test_no_finished_label_recovery(self):
  self.assertFalse(p.parse(self.tr(dict(verdict='Not Supported',reason='x'),'length'),'nsna_plain','x')['valid'])
 def test_inputs_and_settings(self):
  template=dict(model=c.MODEL,enable_thinking=True,reasoning_effort='high',temperature=0,max_tokens=8192,n=1,stream=False)
  for arm in c.REVIEW_ARMS:
   b=p.body(template,'Test done on day1.','Test planned on day1.',arm)
   payload=json.loads(b['messages'][1]['content'].split('## Input JSON:\n')[1]);self.assertEqual(set(payload),{'text','reference'})
   self.assertEqual({k:v for k,v in b.items() if k!='messages'},template)
 def test_budget_unknown(self):
  b=dict(body=dict(max_tokens=8192,messages=[]));v=rt.reserve(b)
  self.assertGreater(v,.073728)
  self.assertEqual(rt.account(b,dict(http_status=0),v)[0],v)
if __name__=='__main__':unittest.main()
