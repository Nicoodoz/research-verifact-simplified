import copy,json,unittest
import format024 as c
def transport(content):
    return dict(http_status=200,body_text=json.dumps(dict(model=c.MODELS['deepseek'],choices=[dict(finish_reason='stop',message=dict(content=content))])))
class FormatRepair(unittest.TestCase):
    def test_identical_duplicates_all_keys_nested(self):
        s='{"verdict":"Supported","verdict":"Supported","reason":"same","reason":"same","checks":[],"label_scores":{"Supported":70,"Supported":70,"Not Supported":20,"Not Addressed":10},"label_scores":{"Supported":70,"Not Supported":20,"Not Addressed":10}}'
        tr=transport(s);before=copy.deepcopy(tr);r=c.parse(tr,True)
        self.assertEqual(r['status'],'success');self.assertEqual(r['scores']['Supported'],70)
        self.assertEqual(tr,before);self.assertEqual(r['output_text'],s)
        self.assertEqual(len(r['format_repair']['folded']),4)
        self.assertEqual(r['format_repair']['original_status'],'invalid')
    def test_conflicting_duplicate_any_key(self):
        for key,a,b in [('verdict','"Supported"','"Not Supported"'),('reason','"a"','"b"'),('checks','[]','[1]')]:
            s='{"verdict":"Supported","reason":"a","checks":[],"'+key+'":'+a+',"'+key+'":'+b+'}'
            self.assertEqual(c.parse(transport(s),False)['status'],'invalid')
    def test_type_sensitive_equality(self):
        for text in ('{"x":1,"x":true}','{"x":1,"x":1.0}','{"x":"1","x":1}','{"x":[1,2],"x":[2,1]}'):
            with self.assertRaises(ValueError):c.fold_json(text,[],'test')
    def test_ordinary_output_exact_semantics(self):
        answer=dict(verdict='Supported',reason='test',checks=[],label_scores={'Supported':75,'Not Supported':20,'Not Addressed':5})
        tr=transport(json.dumps(answer));old=c.old.prior.parse(tr,True);new=c.parse(tr,True)
        for k in old:self.assertEqual(old[k],new[k])
        self.assertEqual(new['format_repair']['folded'],[])
    def test_no_score_fix_or_truncation_fix(self):
        for score in (70,71):
            ans=dict(verdict='Supported',reason='x',checks=[],label_scores={'Supported':score,'Not Supported':20,'Not Addressed':5})
            self.assertEqual(c.parse(transport(json.dumps(ans)),True)['status'],'invalid')
        t=transport('{"verdict":"Supported","reason":"x","checks":[]}')
        n=json.loads(t['body_text']);n['choices'][0]['finish_reason']='length';t['body_text']=json.dumps(n)
        self.assertEqual(c.parse(t,False)['status'],'invalid')
if __name__=='__main__':unittest.main()
