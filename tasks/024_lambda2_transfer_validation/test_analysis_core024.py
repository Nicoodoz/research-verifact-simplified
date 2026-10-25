import unittest
import analyze024_core as a
class FairCohorts(unittest.TestCase):
    def test_pair_specific_intersection(self):
        rows=[dict(proposition_id=str(i),subject_id=str(i%2),human_gt='Supported') for i in range(4)]
        b={'0':'Supported','1':None,'2':'Supported','3':'Supported'}
        s={'0':'Supported','1':'Supported','2':None,'3':'Supported'}
        rr=a.select(rows,[b,s]);self.assertEqual([r['proposition_id'] for r in rr],['0','3'])
        record=a.cohort_record(rows,rr);self.assertEqual(record['excluded_ids'],['1','2']);self.assertEqual(record['expected_n'],4)
        self.assertEqual(len(a.select(rows,[s,s])),3)
    def test_common_model_cohort(self):
        rows=[dict(proposition_id=str(i),subject_id=str(i%2),human_gt='Supported') for i in range(4)]
        d={'0':'Supported','1':'Supported','2':None,'3':'Supported'}
        q={'0':None,'1':'Supported','2':'Supported','3':'Supported'}
        self.assertEqual([r['proposition_id'] for r in a.select(rows,[d,q])],['1','3'])
    def test_same_scores_rescue_harm_accounting(self):
        # Exhaustive integer scores: U2 can only retain U0 or move toS.
        for s in range(101):
            for ns in range(101-s):
                scores={'Supported':s,'Not Supported':ns,'Not Addressed':100-s-ns}
                u0=a.c.old.decision(scores,0);u2=a.c.old.decision(scores,2)
                self.assertTrue(u2==u0 or u2=='Supported')
                for gt in a.c.LABELS:
                    rescue=u0!='Supported' and u2=='Supported' and gt=='Supported'
                    harm=u0==gt!='Supported' and u2=='Supported'
                    self.assertEqual(int(u2==gt)-int(u0==gt),int(rescue)-int(harm))
if __name__=='__main__':unittest.main()
