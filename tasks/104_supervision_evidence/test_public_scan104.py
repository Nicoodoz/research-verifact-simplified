"""Synthetic leakage regression tests; no real keys or clinical records."""
import json
import unittest

from public_scan104 import scan_text,structured_issues


class PublicScanTests(unittest.TestCase):
    def test_claim_slots_relation_and_teacher_body_are_not_public(self):
        for key in ('claim','reference','relation','claim_slots','reasoning_chain','revision_reason','grounding_assessment','retained_teacher_facts','revision_notes','assessment','explanation'):
            value={'private_note':'SYNTHETIC_SENTINEL'} if key=='claim_slots' else 'SYNTHETIC_SENTINEL'
            self.assertTrue(structured_issues({key:value}),key)

    def test_ids_labels_counts_and_SHA_are_allowed(self):
        value={'id':'fixture-id','sid':'fixture-patient','GT':'Not Supported','initial_status':'reference_gap','source_review_sha256':'a'*64,'claim_sha256':'b'*64,'paper_r1_reason_present':True,'counts':{'Supported':5,'Not Supported':3,'Not Addressed':2}}
        self.assertFalse(scan_text(json.dumps(value),'.json'))

    def test_generated_key_and_raw_markers_are_blocked_without_echoing_them(self):
        key='sk-'+'Q'*40
        marker='['+'**'+'synthetic_identifier'+'**'+']'
        date='21'+'14'+'-02'+'-03'
        for value in (key,marker,date):
            found=scan_text(value,'.md')
            self.assertTrue(found)
            self.assertNotIn(value,json.dumps(found))

    def test_schema_column_names_are_not_confused_with_raw_values(self):
        value={'columns':['claim','reference','reason','relation'],'reference_sha256':'c'*64,'reference_chars_mean':12345}
        self.assertFalse(scan_text(json.dumps(value),'.json'))


if __name__=='__main__':unittest.main()
