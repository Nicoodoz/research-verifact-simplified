"""Negative and invariance tests for 013 before charging calls."""
from pathlib import Path
from unittest.mock import patch
import tempfile,unittest,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tasks/013_multi_mechanism_screen'))
import study013 as s
import mechanisms013 as m
from native_stage013 import StageRunner
from score013 import gate_statistics
from verifact_research.inference.siliconflow_pool import Account,save

def passage(text,start):
    return dict(passage_id='p',note_id='1',subject_id='2',text=text[start:],start=start,end_exclusive=len(text)),dict(ROW_ID='1',SUBJECT_ID='2',TEXT=text)

class Screen013Tests(unittest.TestCase):
    def test_single_patient_gain_cannot_pass_screen_gate(self):
        rows=[dict(subject_id=str(i%6),author_type='llm' if i%2 else 'human',human_gt='Supported',baseline='Supported',candidate='Supported') for i in range(30)]
        rows += [dict(subject_id='0',author_type='llm' if i%2 else 'human',human_gt='Supported',baseline='Not Supported',candidate='Supported') for i in range(10)]
        gate=gate_statistics(rows,'baseline','candidate')
        self.assertEqual(gate['net'],10);self.assertFalse(gate['statistical_gate'])
        self.assertFalse(gate['checks']['not_single_patient_dominated'])

    def test_missing_prediction_blocks_even_positive_observed_changes(self):
        rows=[dict(subject_id=str(i%6),author_type='llm' if i%2 else 'human',human_gt='Supported',baseline='Not Supported',candidate='Supported') for i in range(18)]
        rows[0]['candidate']=None
        gate=gate_statistics(rows,'baseline','candidate')
        self.assertFalse(gate['checks']['complete']);self.assertFalse(gate['statistical_gate'])

    def test_operator_recovery_and_no_rewrite(self):
        p,n=passage('Problem: No nausea, no pain.',12)
        q,log=m.repair_passage(p,n)
        self.assertEqual(q['text'],'No nausea, no pain.');self.assertEqual(q['passage_id'],p['passage_id'])
        self.assertEqual(q['end_exclusive'],p['end_exclusive']);self.assertEqual(log['added_characters'],3)

    def test_condition_restored_but_not_crossed_sentence_or_list(self):
        for prefix,expected in [('If aspiration occurs, keep patient\n   ',True),('If aspiration occurs, stop.\n',False),('If aspiration occurs, stop\n7. ',False)]:
            text=prefix+'STRICT NPO';p,n=passage(text,len(prefix));q,_=m.repair_passage(p,n)
            self.assertEqual(q['start']<p['start'],expected)

    def test_intact_negation_not_duplicated(self):
        p,n=passage('Prior No symptoms.\nNo nausea.',18)
        q,_=m.repair_passage(p,n);self.assertEqual(q,p)

    def test_contract_keeps_wrong_literal_subject(self):
        claim='The patient is not enterically coated.';c=m.literal_contract(claim)
        self.assertEqual(c['subject'],'The patient');self.assertEqual(c['subject']+c['predicate'],claim)
        self.assertIsNone(m.literal_contract('Prior to this, Lopressor was given.'))

    def test_cross_patient_repair_rejected(self):
        p,n=passage('No nausea',3);n['SUBJECT_ID']='other'
        with self.assertRaises(AssertionError):m.repair_passage(p,n)

    def test_selector_illegal_id_falls_back_whole_condition(self):
        item={'retrieval':{'C48':{'reference':'original','selected_ids':['real']}}}
        result=m.selected_evidence(item,{},dict(aliases={'p001':'real'}),dict(model=s.CHAT_MODEL,
            choices=[dict(finish_reason='stop',message={'content':'{"selected_ids":["invented"],"reason":"x"}'})]))
        self.assertEqual(result['reference'],'original');self.assertEqual(result['selector_status'],'fallback_invalid_or_missing')

    def test_task_prior_reservation_blocks_next_stage(self):
        class NeverSend:
            def send(self,*args):raise AssertionError('Budget should prevent send')
        with tempfile.TemporaryDirectory(dir=ROOT/'outputs') as tmp,patch.object(s,'OUT',Path(tmp)):
            path=Path(tmp)/'live/earlier';path.mkdir(parents=True)
            save(path/'state.json',dict(used_or_reserved_cny=39.999))
            job=dict(request_id='x',kind='chat',body=dict(model=s.CHAT_MODEL,messages=[{'role':'user','content':'test'}],max_tokens=2048))
            runner=StageRunner('unit_judge',[job],[Account('account_2','FAKE_UNIT_CREDENTIAL')],client=NeverSend())
            result=runner.run(workers=1,retry_wait=0)
            self.assertEqual(result['status_counts'],{'pending':1});self.assertLessEqual(result['cap_cny'],.00100001)
            self.assertEqual(s.total_cost(),39.999)

if __name__=='__main__':unittest.main()
