"""Relevant tests: independent metrics, isolation, original C48 rules, no window gaps."""
import unittest,sys
import numpy as np
import common092 as c
from metrics092 import metrics
class Tests(unittest.TestCase):
    def test_metrics_independent(self):
        from sklearn.metrics import matthews_corrcoef,accuracy_score,f1_score,log_loss
        rng=np.random.RandomState(92)
        for n in [1,20,500]:
            y=rng.randint(0,3,n);q=rng.dirichlet([1,1,1],n);p=q.argmax(1);m=metrics(y,p,q)
            self.assertAlmostEqual(m['MCC'],matthews_corrcoef(y,p));self.assertAlmostEqual(m['PA'],accuracy_score(y,p));self.assertAlmostEqual(m['Macro_F1'],f1_score(y,p,labels=[0,1,2],average='macro',zero_division=0));self.assertAlmostEqual(m['NLL'],log_loss(y,q,labels=[0,1,2]))
    def test_patient_isolation(self):
        folds=c.read(c.OUT/'folds.json');tests=[]
        for f in folds:
            self.assertFalse(set(f['train'])&set(f['validation']));self.assertFalse(set(f['train']+f['validation'])&set(f['test']));self.assertEqual(len(set(f['train']+f['validation']+f['test'])),100);tests+=f['test']
        self.assertEqual(len(tests),len(set(tests)));self.assertEqual(len(tests),100)
    def test_windows_cover_all_original_tokens(self):
        from transformers import AutoTokenizer
        from cache092 import windows
        tok=AutoTokenizer.from_pretrained(c.ROOT/'.local_models/032/deberta_v3_nli',local_files_only=True);cfg=c.read(c.TASK/'config.json')
        for reference in ['', 'A measurement was repeated. '*1200]:
            ww,n=windows(tok,'The measurement was repeated.',reference,cfg)
            self.assertEqual(len({i for w in ww for i in range(w['evidence_start'],w['evidence_end'])}),n);self.assertTrue(all(len(w['input_ids'])<=512 for w in ww))
    def test_C48_exact_original_selection(self):
        from local_c48 import original_rules
        rule=original_rules();rows=c.lines(c.ROOT/'outputs/009_retrieval_baselines/development_001/judge_preparation/inputs.jsonl');corpus=c.lines(c.ROOT/'outputs/009_retrieval_baselines/development_001/preparation/corpus.jsonl');byid={p['passage_id']:p for p in corpus}
        for r in rows:
            pack=rule.core.select_evidence(r['retrieval']['C48']['candidate_ids'],r['scores'],byid,r['admission']);self.assertEqual(pack['reference'],r['retrieval']['C48']['reference'])
    def test_probability_risk_denominators(self):
        m=metrics([0,1,2,2],[0,0,0,2]);self.assertEqual(m['false_S'],2);self.assertEqual(m['false_S_rate'],2/3);self.assertEqual(m['false_discovery_S'],2/3)
if __name__=='__main__':unittest.main()
