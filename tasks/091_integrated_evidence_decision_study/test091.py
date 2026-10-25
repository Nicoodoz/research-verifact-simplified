import unittest
from common091 import *
from c_materials091 import witness,quantities
from selective091 import action,matched_margin_ids

class Tests(unittest.TestCase):
    def test_exact_numeric_boundary_and_unit(self):
        self.assertTrue(witness('Device A: 45 mm Hg.','Device A: 145 mm Hg.')['missing'])
        self.assertTrue(witness('Device A: 45 mm Hg.','Device A: 45 cm H2O.')['missing'])
        self.assertFalse(witness('Device A: 45.0 mm Hg.','Device A: 45 mmHg.')['missing'])
    def test_metadata_is_not_numeric_evidence(self):
        ref='1. Date: 45 mm Hg, Time: 0, Note Category: synthetic, Note ID: fake, Raw characters: [0,13) | Text: Device absent.'
        self.assertTrue(witness('Device A: 45 mm Hg.',ref)['missing'])
    def test_literal_presence_is_not_sufficiency(self):
        out=action('Device A: 5 mg.','Device B: 5 mg.','Supported')
        self.assertEqual(out['action'],'retain_baseline');self.assertEqual(out['evidence_sufficiency'],'unknown')
        self.assertFalse(witness('Device A: 5 mg.','Device A did not receive 5 mg.')['missing'])
    def test_defer_is_not_relabel(self):
        x=action('Device A: 5 mg.','No measurement.','Supported')
        self.assertEqual(x['action'],'defer');self.assertEqual(x['original_label'],'Supported')
        self.assertEqual(action('Device A: 5 mg.','No measurement.','Not Addressed')['action'],'retain_baseline')
    def test_matched_workload_and_ties(self):
        rows=[dict(id=str(i),scores=dict(zip(LABELS,[10,85,5])),final_label='Supported',eligible=i<2) for i in range(4)]
        self.assertEqual(len(matched_margin_ids(rows,2)),2)
        self.assertEqual(set(matched_margin_ids(rows,2,True)),{'0','1'})
        self.assertEqual(matched_margin_ids(rows,2),matched_margin_ids(list(reversed(rows)),2))
        with self.assertRaises(ValueError):matched_margin_ids(rows,3,True)
    def test_deterministic_score_layers(self):
        for s in (dict(zip(LABELS,[10,20,70])),dict(zip(LABELS,[15,75,10])),dict(zip(LABELS,[0,95,5]))):
            self.assertEqual(priorg(s),LABELS[int(np.argmax(logs(s)+GB))])
        s=dict(zip(LABELS,[10,20,70]));self.assertEqual(prior_only(s),'Not Addressed');self.assertEqual(priorg(s),'Supported')
    def test_constant_bias_preserves_pair_ranking(self):
        for c,d in ((0,1),(0,2),(1,2)):
            a=logs(dict(zip(LABELS,[15,75,10])));b=logs(dict(zip(LABELS,[10,20,70])))
            self.assertAlmostEqual((a[c]-a[d])-(b[c]-b[d]),((a+GB)[c]-(a+GB)[d])-((b+GB)[c]-(b+GB)[d]))

if __name__=='__main__':unittest.main()
