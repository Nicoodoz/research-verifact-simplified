"""Focused CPU tests: exact task parity, parser, no truncation, verdict-only mask."""
import unittest,json,sys
import common103 as c
from prompt103 import messages
from parse103 import parse_content
from gpu_worker103 import encode_lists
class FakeTokenizer:
 def apply_chat_template(self,msgs,**kwargs):return self.encode(json.dumps(msgs),add_special_tokens=False)
 def encode(self,s,**kwargs):return [ord(x) for x in s]
 def decode(self,ids):return ''.join(chr(x) for x in ids)
 def convert_tokens_to_ids(self,s):return 999999
class Tests(unittest.TestCase):
 def test_mask(self):
  r={'claim':'claim','reference':'long reference '*20000,'GT':'Not Supported'};ids,labels,n=encode_lists(FakeTokenizer(),r);split=len(ids)-n
  self.assertGreater(len(ids),200000);self.assertTrue(all(x==-100 for x in labels[:split]));self.assertEqual(ids[split:],labels[split:]);self.assertEqual(FakeTokenizer().decode(labels[split:-1]),'{"verdict":"Not Supported"}')
 def test_parser(self):
  self.assertTrue(parse_content('```json\n{"verdict":"Not Addressed"}\n```','stop')['valid'])
  self.assertFalse(parse_content('{"verdict":"Supported","verdict":"Not Supported"}')['valid'])
  self.assertFalse(parse_content('Probably Supported.')['valid'])
 def test_prompt(self):
  ref='FULL REFERENCE LAST MARKER';native=messages('claim',ref,'native')[1]['content'];label=messages('claim',ref,'label')[1]['content'];self.assertIn(ref,native);self.assertIn(ref,label);self.assertIn('only partially supported',label);self.assertEqual(native.split('4. Provide a reason')[0],label.split('4. Format')[0])
 def test_patient_roles(self):
  groups=c.read(c.OUT/'patient_roles.json')['patients'];self.assertEqual([len(groups[k]) for k in ['train','selection','confirmation']],[40,20,40]);self.assertEqual(len(set(sum(groups.values(),[]))),100)
 def test_panels(self):
  train=c.lines(c.PRIVATE/'train512.jsonl');sample=c.lines(c.PRIVATE/'sample240.jsonl');self.assertFalse({r['sid'] for r in train}&{r['sid'] for r in sample});self.assertEqual(len({r['id'] for r in sample}),240);self.assertEqual(sum(r['local180'] for r in sample),180);self.assertEqual(sum(r['direct48'] for r in sample),48)
  from collections import Counter
  self.assertEqual(dict(Counter(r['GT'] for r in train[:256])),{'Supported':160,'Not Supported':48,'Not Addressed':48})
if __name__=='__main__':unittest.main()
