"""Offline checks for incomplete/ambiguous output protection."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import common024 as c
import analyze024
class Closure(unittest.TestCase):
    def test_incomplete_has_no_metrics(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'never_created'
            with patch.object(c,'verify_inputs',return_value=[]),patch.object(c,'load_attempts',return_value=([],{})):
                with self.assertRaises(ValueError):analyze024.run(p)
            self.assertFalse(p.exists())
    def test_identical_duplicate_still_invalid_under_original_parser(self):
        answer='{"verdict":"Supported","reason":"same","reason":"same","checks":[]}'
        tr=dict(http_status=200,body_text=json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content=answer))])))
        self.assertEqual(c.old.prior.parse(tr,False)['errors'],['Duplicate JSON key'])
    def test_conflicting_duplicate_invalid(self):
        answer='{"verdict":"Supported","reason":"a","reason":"b","checks":[]}'
        tr=dict(http_status=200,body_text=json.dumps(dict(choices=[dict(finish_reason='stop',message=dict(content=answer))])))
        self.assertEqual(c.old.prior.parse(tr,False)['status'],'invalid')
if __name__=='__main__':unittest.main()
