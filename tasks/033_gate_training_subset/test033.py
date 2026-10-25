import unittest
import numpy as np
import common033 as s

class Tests(unittest.TestCase):
    def test_declared_scope(self):
        rows=s.lines(s.PREP/'rows_selection_blind.jsonl');split=s.read(s.PREP/'split.json');old=set(split['original16']);search=set(split['expansion12']);check=set(split['confirmation12']);self.assertEqual((len(old),len(search),len(check)),(16,12,12));self.assertFalse((old&search)|(old&check)|(search&check));self.assertEqual(len(rows),3675);self.assertTrue(all(r['human_gt'] is None for r in rows if r['subject_id'] in check))
    def test_original_features_exact(self):
        rows={r['proposition_id']:r for r in s.lines(s.PREP/'rows_selection_blind.jsonl')}
        for r in s.lines(s.old.PREP/'features.jsonl'):
            for m in ('A','B','D'):self.assertEqual([r['features'][k] for k in s.c.FEATURES[m]],[rows[r['proposition_id']]['features'][k] for k in s.c.FEATURES[m]])
    def test_rejected_candidate_U0(self):
        rr=[dict(proposition_id='a',candidate=True,u0=1),dict(proposition_id='b',candidate=False,u0=2),dict(proposition_id='c',candidate=True,u0=2)];self.assertEqual(s.pred(rr,[.2,.8],.5).tolist(),[1,2,0])
    def test_curves_do_not_change_workpoint(self):
        rr=[dict(proposition_id='a',candidate=True,u0=1),dict(proposition_id='b',candidate=False,u0=2)];ts,pp=s.curves(rr,[.7],.8);self.assertEqual(pp[0].tolist(),[1,2]);self.assertTrue(np.all(pp[:,1]==2));self.assertIn([0,2],pp.tolist())

if __name__=='__main__':unittest.main()
