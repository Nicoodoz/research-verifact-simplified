import copy,unittest,json
import common095 as c
import method095 as m

class Safety(unittest.TestCase):
    def setUp(self):
        self.row=dict(text='The tube was removed on day 2.',reference='1. Date: day 2, Time: 09:00, Note Category: Synthetic, Note ID: 0, Raw characters: [0,60) | Text: The tube was retained on day 2.\nRemoval was planned for day 3.')
        self.v=dict(applicable=True,attribute='state',old_span='removed',new_span='retained',source_value='retained',anchors=[dict(reference_id=1,quote='The tube was retained on day 2.')])
    def test_only_one_edit_and_exact_source(self):
        v=m.validate(self.v,self.row);self.assertTrue(v['valid']);self.assertEqual(v['alternative'],'The tube was retained on day 2.')
        for a in v['anchors']:self.assertEqual(self.row['reference'][a['reference_start']:a['reference_end']],a['quote'])
        bad=copy.deepcopy(self.v);bad['anchors'][0]['quote']='The tube was removed on day 2.';self.assertFalse(m.validate(bad,self.row)['valid'])
    def test_header_date_cannot_be_source(self):
        bad=copy.deepcopy(self.v);bad['anchors'][0]['quote']='Date: day 2';self.assertFalse(m.validate(bad,self.row)['valid'])
    def test_gt_and_prior_output_never_in_payload(self):
        row=dict(self.row,GT='SECRET_LABEL',old_reason='SECRET_REASON',original='SECRET_AUTHOR')
        v=m.validate(self.v,row);b=m.builder(row);ch=m.checker(row,v)
        for body in [b,ch]:
            self.assertNotIn('SECRET',c.canonical(body));self.assertNotIn('GT',json.loads(body['messages'][1]['content']))
    def test_matched_ec_and_identical_b(self):
        t=c.read(c.PRIVATE/'judge_template.json');v=m.validate(self.v,self.row);e=m.judge(t,self.row,'E',v);co=m.judge(t,self.row,'C',v)
        ep=json.loads(e['messages'][1]['content']);cp=json.loads(co['messages'][1]['content']);cp.pop('alternative_hypothesis');self.assertEqual(ep,cp);self.assertEqual(e['messages'][0],co['messages'][0]);self.assertEqual(ep['reference'],self.row['reference'])
        b=m.judge(t,self.row);self.assertEqual(b['messages'][0],t['messages'][0]);self.assertEqual(set(json.loads(b['messages'][1]['content'])),{'proposition','reference'})
    def test_checker_not_truth_gate(self):
        tr={'body_text':json.dumps({'choices':[{'message':{'content':json.dumps(dict(single_property=True,substantive_difference=True,source_value_supported=True,same_event_context=False,no_invented_fact=True))}}]})}
        self.assertFalse(m.parse_checker(tr)['valid'])

if __name__=='__main__':unittest.main()
