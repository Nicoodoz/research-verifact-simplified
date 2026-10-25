import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import common096 as c
import marlin096 as m
class Tests(unittest.TestCase):
    def test_same_samples_new_cache(self):
        old=c.lines(m.OLD_P/'jobs.jsonl');new=c.lines(m.P/'jobs.jsonl');self.assertEqual(len(old),len(new));self.assertEqual([x['id'] for x in old],[x['id'] for x in new])
        for a,b in zip(old,new):self.assertEqual(a['body'],b['body']);self.assertNotEqual(a['request_id'],b['request_id']);self.assertEqual(b['backend_id'],m.BACKEND)
        for name,h in c.read(m.OLD_O/'freeze.json')['files'].items():
            self.assertEqual(c.sha(m.OLD_O/name),h)
            if name!='request_manifest.jsonl':self.assertEqual(c.sha(m.O/name),h)
    def test_atomic_and_never_resend_http200(self):
        with tempfile.TemporaryDirectory() as td,patch.object(m,'P',Path(td)),patch.object(m.r,'P',Path(td)),patch.object(m.r,'request',return_value=(c.encoded({'model':c.MODEL}),dict(http_status=200,outcome_unknown=False))) as req:
            j=dict(id='x',request_id='x',body={},body_sha256=c.digest({}));m.invoke(j,'M0');m.invoke(j,'M0');self.assertEqual(req.call_count,1);self.assertFalse(list(Path(td).rglob('*.pending')))
    def test_old_success_not_new_success(self):
        new=c.lines(m.P/'jobs.jsonl')[0]
        with patch.object(m.r,'P',m.P):self.assertIsNone(m.r.success(new))
if __name__=='__main__':unittest.main()
