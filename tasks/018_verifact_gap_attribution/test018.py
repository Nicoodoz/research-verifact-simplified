"""Negative controls for audit integrity; uses only the frozen exposed cohort."""
import copy,unittest
import common018 as c
from verify018 import validate_rows

class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=c.jsonlines(c.OUT/'preparation_001/ledger.jsonl')
        cls.cohort=c.csvrows(c.OUT/'preparation_001/cohort.csv')
    def check_rejected(self,rows,cohort=None):
        with self.assertRaises((ValueError,AssertionError,RuntimeError)):
            validate_rows(rows,cohort or self.cohort)
    def test_complete(self):validate_rows(self.rows,self.cohort)
    def test_missing(self):self.check_rejected(self.rows[:-1])
    def test_duplicate_replaces_claim(self):self.check_rejected(self.rows[:-1]+[self.rows[0]])
    def test_foreign_claim(self):
        rows=copy.deepcopy(self.rows);rows[0]['proposition_id']='foreign';self.check_rejected(rows)
    def test_gt_changed(self):
        rows=copy.deepcopy(self.rows);rows[0]['human_gt']='Not Addressed' if rows[0]['human_gt']!='Not Addressed' else 'Supported';self.check_rejected(rows)
    def test_patient_changed(self):
        rows=copy.deepcopy(self.rows);rows[0]['subject_id']='outside_cohort';self.check_rejected(rows)
    def test_illegal_prediction(self):
        rows=copy.deepcopy(self.rows);rows[0]['C']='invalid';self.check_rejected(rows)
    def test_bucket_changed(self):
        rows=copy.deepcopy(self.rows);rows[0]['bucket']='not_a_bucket';self.check_rejected(rows)

if __name__=='__main__':unittest.main()
