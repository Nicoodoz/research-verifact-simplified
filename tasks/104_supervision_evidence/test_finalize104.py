"""Regression: sampled failures cannot silently enter the final paired package."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import common104 as c
import finalize104 as f


class FinalizeTests(unittest.TestCase):
    def fixture(self,root):
        private=root/'private';out=root/'out';private.mkdir();out.mkdir()
        source=dict(id='same-input',GT='Not Supported',answer=c.canonical(dict(evidence=['given'],relation='The claimed dose differs from the given dose.',verdict='Not Supported')),
                    metadata=dict(teacher_review={'id':'same-input'},relation_origin='existing_teacher_revised',teacher_semantic_reviewed=True))
        c.put(out/'candidate_teacher_checked_manifest.json',dict(all_teacher_comparisons_complete=True,pending=0,files={},N=1))
        c.put(out/'candidate_paired_manifest.json',dict(N=1))
        c.putl(private/'review_joined_initial.jsonl',[
            dict(id='same-input',GT='Not Supported',initial_status='candidate_gt_explained',na_anchor='not_applicable'),
            dict(id='blind-disagreement',GT='Not Supported',initial_status='reference_gap')])
        c.putl(private/'candidate_teacher_checked/evidence_brief.jsonl',[source])
        c.putl(private/'teacher_decision_history.jsonl',[dict(id='same-input')])
        c.putl(private/'api_quality_reviews.jsonl',[dict(id='same-input',phase='quality',request_id='r1',result=dict(valid=True,recommendation='revise',checks={'qualifiers_preserved':False},critical_issues=[{'type':'dose','explanation':'Ambiguous dose'}]))])
        c.putl(private/'api_jobs.jsonl',[dict(request_id='r1')])
        return private,out

    def test_flag_requires_documented_semantic_decision(self):
        with tempfile.TemporaryDirectory() as folder:
            private,out=self.fixture(Path(folder))
            with patch.object(c,'PRIVATE',private),patch.object(c,'OUT',out):
                with self.assertRaisesRegex(ValueError,'explicit semantic decision'):f.finalize()
            self.assertFalse((private/'final_decisions.jsonl').exists())

    def test_teacher_revision_survives_and_disagreement_is_not_rescued(self):
        with tempfile.TemporaryDirectory() as folder:
            private,out=self.fixture(Path(folder))
            c.putl(private/'post_audit_decisions.jsonl',[dict(id='same-input',action='revise',reviewer='reviewer',assessment='Explicitly bound dose after rereading same reference.',relation='Only the original drug dose is used; the other dose belongs to another drug.',revision_notes='Separate drug identities.')])
            def build(_private,_out,path):
                rows=c.lines(path)
                self.assertEqual(rows[0]['relation'],'Only the original drug dose is used; the other dose belongs to another drug.')
                self.assertEqual(rows[0]['supervision_metadata']['relation_origin'],'existing_teacher_revised')
                self.assertFalse(rows[1]['quality_approved'])
                self.assertEqual(rows[1]['final_status'],'reference_gap')
                return dict(N=1,retained_GT={'Not Supported':1})
            with patch.object(c,'PRIVATE',private),patch.object(c,'OUT',out),patch.object(f.b,'build',side_effect=build):
                self.assertEqual(f.finalize()['N'],1)


if __name__=='__main__':unittest.main(verbosity=2)
