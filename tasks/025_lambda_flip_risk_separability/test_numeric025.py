import unittest
import numpy as np
import frontier025_numeric as f
class NumericCounts(unittest.TestCase):
    def test_boolean_mask_counts_claims_not_any(self):
        rows=[dict(u0=1,human_gt='Supported') for _ in range(5)]+[dict(u0=2,human_gt='Not Addressed') for _ in range(3)]
        p=np.zeros(8,dtype=int);mask=np.array([True]*4+[False]+[True]*2+[False])
        r,risk=f.counts(rows,p,mask);self.assertEqual(r[0],4);self.assertEqual(risk[0],2)
        r2,f2=f.counts(rows,p,mask.astype(int));np.testing.assert_array_equal(r,r2);np.testing.assert_array_equal(risk,f2)
if __name__=='__main__':unittest.main()
