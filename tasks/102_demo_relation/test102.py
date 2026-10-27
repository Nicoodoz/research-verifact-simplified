import unittest
import selector102 as s
class RelationTests(unittest.TestCase):
 def test_reference_changes_pair(self):
  claim='The medication was administered after surgery.'
  a,_=s.relation_features(claim,'The medication was administered after surgery.')
  b,_=s.relation_features(claim,'Medication was planned before surgery; it was not administered.')
  self.assertNotEqual(a,b);self.assertTrue(any(k.startswith('pair/') and 'plan' in k for k in b))
 def test_sources_exact(self):
  ref='1. Date: 2020-01-01, Note: example | Text: Medication was planned but not given.'
  _,a=s.relation_features('Medication was given.',ref)
  self.assertTrue(a['windows'])
  for w in a['windows']:self.assertEqual(s.c.digest(ref[w['start']:w['end']]),w['sha256'])
 def test_no_match_not_fake_evidence(self):
  f,a=s.relation_features('Creatinine increased.','A completely unrelated administrative note.')
  self.assertFalse(a['reference_used']);self.assertEqual(f['pair/no_anchor_window'],1.)
 def test_no_outcome_labels(self):
  f,a=s.relation_features('Medication was given.','Medication was not given.')
  self.assertFalse(any('supported' in k.lower() or 'contradiction' in k.lower() or 'verdict' in k for k in f))
if __name__=='__main__':unittest.main()
