"""011 clinically meaningful source-integrity and budget invariants, offline only."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/011_evidence_integrity_packaging'))
import study011 as s
import packaging011 as p

def passage(text,lo=0,hi=None,category='Nursing'):
    hi=len(text) if hi is None else hi
    note=dict(ROW_ID='1',SUBJECT_ID='2',TEXT=text,DESCRIPTION='Real description')
    piece=dict(note_id='1',subject_id='2',start=lo,end_exclusive=hi,text=text[lo:hi],note_sha256=s.pilot.digest_text(text),
        description=note['DESCRIPTION'],category=category,date='[CLINICAL_LITERAL_REMOVED]',time='00:00:00')
    return piece,note

class IntegrityPackagingTests(unittest.TestCase):
    def test_conditional_list_restores_all_sentences_of_item(self):
        text='RECOMMENDATIONS:\n1. Give pills.\n2. Maintain precautions. If there are concerns, keep patient\n   STRICT NPO.\n3. Continue monitoring.'
        lo=text.index('STRICT');hi=text.index('3.');piece,note=passage(text,lo,hi-1)
        v=p.make_views(piece,note)
        self.assertIn('2. Maintain precautions. If there are concerns',v['B']['text'])
        self.assertNotIn('1. Give pills',v['B']['text'])
    def test_unbounded_sentence_not_guessed_or_summarized(self):
        text='If '+('several conditions '*40)+'then give medicine.'
        lo=text.index('then');piece,note=passage(text,lo)
        v=p.make_views(piece,note)
        self.assertIn('left_boundary_beyond_240',v['B']['repair']['unresolved'])
        self.assertEqual(v['B']['text'],piece['text'])
    def test_same_note_patient_and_hash_are_mandatory(self):
        piece,note=passage('A finding.');note['SUBJECT_ID']='3'
        with self.assertRaises(AssertionError):p.make_views(piece,note)
    def test_echo_single_test_context_and_ambiguous_test_abstention(self):
        text='Test: Portable TTE (Complete)\n\nIMPRESSION:\nNormal function.'
        piece,note=passage(text,text.index('Normal'),category='Echo')
        v=p.make_views(piece,note)
        self.assertIn('unique_note_test',[x['kind'] for x in v['C']['source_context']])
        text+='\nTest: Different examination'
        piece,note=passage(text,text.index('Normal'),text.index('\nTest:'),category='Echo')
        self.assertNotIn('unique_note_test',[x['kind'] for x in p.make_views(piece,note)['C']['source_context']])
    def test_heading_not_carried_across_new_section(self):
        text='FINDINGS:\nNormal function.\nPLAN:\nObserve.'
        piece,note=passage(text,text.index('Normal'))
        v=p.make_views(piece,note)
        self.assertFalse(v['C']['source_context'])
    def test_lowercase_field_and_unlabelled_paragraph_stop_heading_scope(self):
        text='PMHx:\nOld history.\nCurrent medications:\nTake medicine.'
        piece,note=passage(text,text.index('Take'))
        self.assertNotIn('PMHx:',[h['text'] for h in p.make_views(piece,note)['C']['source_context']])
        text='INDICATION: Something.\n\nProcedure happened.'
        piece,note=passage(text,text.index('Procedure'))
        self.assertFalse(p.make_views(piece,note)['C']['source_context'])
    def test_report_divider_does_not_inherit_exam_reason(self):
        text='REASON FOR EXAM:\nPossible disease.\n_______________\nFINAL REPORT\nNo disease.'
        piece,note=passage(text,text.index('Possible'))
        self.assertFalse(p.make_views(piece,note)['C']['source_context'])
    def test_wrapped_parenthetical_field_is_not_an_end_boundary(self):
        text='Exam: Right leg (Pulse -\n Dorsalis pedis: Present).\nPlan: Observe.'
        piece,note=passage(text,0,text.index('Dorsalis')-2)
        self.assertIn('Dorsalis pedis: Present)',p.make_views(piece,note)['B']['text'])
    def test_repair_preserves_original_text_and_budget_includes_metadata(self):
        text='Whole sentence contains the finding.'
        piece,note=passage(text,text.index('contains'),text.index('finding'))
        v=p.make_views(piece,note)
        self.assertIn(piece['text'],v['B']['text'])
        admission=dict(ADMITTIME='a',DISCHTIME='b')
        cap=len(p.display(1,piece,'A'))+1
        a=p.pack(['k'],{'k':1},{'k':v},admission,'A',cap)
        b=p.pack(['k'],{'k':1},{'k':v},admission,'B',cap)
        self.assertEqual(a['selected_ids'],['k'])
        self.assertEqual(b['selected_ids'],[])
        self.assertEqual(b['selection_skips'][0]['reason'],'character_cap')
    def test_no_missing_score_or_claim_dependent_repair(self):
        piece,note=passage('Normal function.');v=p.make_views(piece,note)
        with self.assertRaises(AssertionError):p.pack(['k'],{}, {'k':v},{},'B')
        self.assertEqual(v,p.make_views(piece,note))

if __name__=='__main__':unittest.main()
