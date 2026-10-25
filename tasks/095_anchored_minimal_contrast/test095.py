import unittest,json,sqlite3,tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import common095 as c
from cache095 import signature
from run095 import charge
class Checks(unittest.TestCase):
    def test_cache_identity(self):
        b=c.read(c.PRIVATE/'judge_template.json');s=signature(b)
        for k,v in [('n',1),('stream',False),('top_p',1)]:b[k]=v
        self.assertEqual(signature(b),s);b['messages'][0]['content']+=' additional hint';self.assertNotEqual(signature(b),s)
    def test_billing(self):
        j={'bound_cny':1};tr={'body_text':json.dumps({'usage':{'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':{'cached_tokens':200}}})}
        self.assertAlmostEqual(charge(j,tr),.00336);self.assertEqual(charge(j,None),1)
    def test_atomic_parallel_cap(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'ledger.db';db=sqlite3.connect(path);db.execute('CREATE TABLE a(v REAL)');db.commit();db.close()
            def reserve(_):
                db=sqlite3.connect(path,timeout=30);db.execute('BEGIN IMMEDIATE');used=db.execute('SELECT COALESCE(SUM(v),0) FROM a').fetchone()[0]
                if used+.1<=1+1e-9:db.execute('INSERT INTO a VALUES(.1)');db.commit();ok=True
                else:db.rollback();ok=False
                db.close();return ok
            with ThreadPoolExecutor(max_workers=8) as p:results=list(p.map(reserve,range(30)))
            self.assertEqual(sum(results),10)
    def test_fixed_reference(self):
        inp={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')};jobs=c.lines(c.PRIVATE/'baseline_jobs.jsonl')
        self.assertEqual(len(jobs),7180)
        for j in jobs:
            p=json.loads(j['body']['messages'][1]['content']);self.assertEqual(p,dict(proposition=inp[j['id']]['text'],reference=inp[j['id']]['reference']))
if __name__=='__main__':unittest.main()
