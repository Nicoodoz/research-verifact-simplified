"""Offline contract tests; no patient gold needed, no network."""
import copy,unittest,json
import common044 as c
import selector044 as s
class Contracts(unittest.TestCase):
    def setUp(self):
        self.ps={str(i):dict(passage_id=str(i),date='[CLINICAL_LITERAL_REMOVED]',time='12:00:00',category='Nursing',
          note_id=str(i),start=0,end_exclusive=20,text='Plan for scan' if i<2 else ('Scan cancelled today' if i==2 else 'Scan completed next day'),
          search_text='Scan',subject_id='p') for i in range(4)}
        self.base='Hospital context\n1. '+c.pc.display_line(1,self.ps['0']).split('. ',1)[1]
        self.score={str(i):1-i*.1 for i in range(4)}
    def test_prefix_budget_and_dedup(self):
        out=s.propose('Scan was performed',self.base,['0'],list(self.ps),self.score,self.ps)
        for p in out.values():
            self.assertTrue(p['reference'].startswith(self.base)); self.assertLessEqual(p['added_chars'],1500)
            self.assertNotIn('1',p['ids']); self.assertEqual(len(p['features']),len(s.FEATURES))
            self.assertTrue(set(p['ids'])<=set(self.ps)); self.assertLessEqual(len(p['ids']),2)
    def test_no_mutation(self):
        saved=copy.deepcopy(self.ps); s.propose('Scan',self.base,['0'],list(self.ps),self.score,self.ps)
        self.assertEqual(self.ps,saved)
    def test_empty(self):
        out=s.propose('Scan',self.base,['0'],['0'],{'0':1},self.ps)
        for p in out.values(): self.assertEqual(p['reference'],self.base); self.assertEqual(p['ids'],[])
    def test_contradictory_material_not_filtered(self):
        out=s.propose('Scan was performed',self.base,['0'],['0','2'],self.score,self.ps)
        self.assertEqual(out['rank']['ids'],['2'])
    def test_reason_must_cover_whole_claim(self):
        a=dict(status='valid',reason_label='Supported',evidence_label='Supported',grounding='full',coverage='partial',citation_valid=True)
        self.assertFalse(c.joint_ok(a,'Supported')); a['coverage']='complete'; self.assertTrue(c.joint_ok(a,'Supported'))
    def test_semantic_and_literal_are_separate(self):
        a=dict(status='valid',reason_label='Supported',evidence_label='Not Supported',grounding='full',coverage='complete',citation_valid=True)
        self.assertFalse(c.joint_ok(a,'Supported'))
        a['evidence_label']='Supported'; a['citation_valid']=False; self.assertFalse(c.joint_ok(a,'Supported'))
    def test_existing_lambda_decoder(self):
        x={'Supported':20,'Not Supported':70,'Not Addressed':10}
        self.assertEqual(c.ulabel(x,0),'Not Supported'); self.assertEqual(c.ulabel(x,2),'Supported')
    def test_exact_quote(self):
        self.assertTrue(c.quote_match('Scan   cancelled','Scan cancelled today'))
        self.assertFalse(c.quote_match('Scan completed','Scan cancelled today'))
if __name__=='__main__': unittest.main(verbosity=2)
