"""Offline017 scope, attribution and budget guards; no real HTTP."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import sys
import unittest
from unittest.mock import patch
from contextlib import ExitStack,redirect_stdout
from types import SimpleNamespace
import tempfile,io
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/017_verification_supervised_evidence_utility'))
import common017 as c
from selection017 import interventions,features
from gate017 import assess
import run017
from verifact_research.inference.aliyun import Config

class UtilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=c.jsonlines(c.OUT/'preparation_001/inputs.jsonl')
        _,cls.passages,_=c.sources()

    def test_fixed_disjoint_patients_and_blind_sample(self):
        plan=c.read(c.OUT/'preparation_001/sampling.json')
        self.assertFalse(set(plan['train_patients'])&set(plan['selection_patients']))
        self.assertEqual(Counter((r['subject_id'],r['author_type']) for r in self.rows).most_common()[0][1],8)
        self.assertEqual(len(self.rows),192)
        order=c.old.baseline.patient_order();self.assertEqual(set(plan['train_patients']+plan['selection_patients']),set(order[18:30]))
        self.assertFalse(set(order[30:])&{r['subject_id'] for r in self.rows})

    def test_all_swaps_are_single_intact_budget_matched(self):
        for r in self.rows:
            for arm in c.SWAPS:
                v=r['interventions'][arm]
                if not v['eligible']:continue
                old=set(r['baseline']['selected_ids']);new=set(v['selected_ids'])
                self.assertEqual(new-old,{v['added']});self.assertEqual(old-new,{v['removed']})
                self.assertEqual(len(old),len(new));self.assertLessEqual(v['body_characters'],8000)
                self.assertLessEqual(max(Counter(self.passages[k]['note_id'] for k in new).values()),2)
                self.assertTrue(.9<=v['length_ratio']<=1.1)
                self.assertEqual(len(v['features_in']),len(c.FEATURES))

    def test_GT_and_identity_not_features_or_interventions(self):
        item=deepcopy(self.rows[0]);base=interventions(item,self.passages)
        item.update(human_gt='Not Supported',old_verdict='Supported',author_type='arbitrary',subject_id='other-person',split='other')
        self.assertEqual(base,interventions(item,self.passages))
        for arm in c.SWAPS:
            if base[arm]['eligible']:
                v=base[arm];self.assertEqual(v['features_in'],features(item,v['added'],v['kept'],self.passages))

    def test_no_hidden_Judge_fields_and_independent_rounds(self):
        jobs={j['request_id']:j for j in c.jsonlines(c.OUT/'preparation_001/jobs.jsonl')}
        assign=c.csvrows(c.OUT/'preparation_001/assignments.csv')
        for j in jobs.values():
            self.assertEqual(set(c.old.pilot.strict_json(j['body']['messages'][1]['content'])),{'proposition','reference'})
            self.assertEqual(j['body']['model'],c.MODEL);self.assertFalse(j['body']['enable_thinking'])
        by={}
        for a in assign:by.setdefault((a['proposition_id'],a['arm']),{})[a['repeat']]=a['request_id']
        for v in by.values():
            self.assertNotEqual(v['0'],v['1']);self.assertEqual(jobs[v['0']]['body'],jobs[v['1']]['body'])

    def test_noop_cannot_rescue_and_cross_provider_not_supervision(self):
        r=deepcopy(self.rows[0]);pid=r['proposition_id'];truth={pid:'Supported'}
        labels={(pid,arm,k):'Not Supported' for arm in c.ARMS for k in (0,1)}
        providers={key:'siliconflow' for key in labels}
        for k in (0,1):labels[(pid,'c48_local',k)]='Supported'
        _,cases,events=assess([r],labels,truth,providers);self.assertTrue(cases[0]['rescued'])
        providers[(pid,'c48_local',1)]='aliyun'
        _,cases,events=assess([r],labels,truth,providers);self.assertFalse(cases[0]['rescued'])
        self.assertTrue(all(e['utility']==0 for e in events))

    def test_whole80_forecast_and_durable_single_success(self):
        with tempfile.TemporaryDirectory() as temp,ExitStack() as stack:
            out=Path(temp);(out/'preparation_001').mkdir();(out/'live').mkdir()
            j=dict(request_id='synthetic',kind='chat',proposition_id='fake',case_id='fake',body=dict(model=c.MODEL,messages=[dict(role='user',content='synthetic')],max_tokens=2048))
            c.write_lines(out/'preparation_001/jobs.jsonl',[j]);c.write_json(out/'preparation_001/summary.json',dict(confirmation_planning_allowance_cny=0))
            (out/'protocol_001.md').write_text('synthetic',encoding='utf-8');c.write_json(out/'execution_policy_001.json',{})
            c.write_json(out/'authority_001.json',dict(execution_sha256={},protocol_sha256=c.file_hash(out/'protocol_001.md'),execution_policy_sha256=c.file_hash(out/'execution_policy_001.json')))
            c.write_json(out/'live/ledger.json',dict(cap_cny=80,used_or_reserved_cny=0.,phases={},provider='siliconflow',exhausted_accounts=[]))
            stack.enter_context(patch.object(c,'OUT',out));stack.enter_context(patch.object(c,'check'))
            stack.enter_context(patch.object(run017,'GLOBAL_ROUTE',out/'route.json'))
            stack.enter_context(patch.object(run017,'load_config',return_value=Config('fake-key')))
            stack.enter_context(patch.object(c.old,'load_accounts',return_value=[SimpleNamespace(alias='account_2',key='fake-other-key')]))
            calls=[];outer=self
            class FakeClient:
                def send(self,account,job):
                    ledger=c.read(out/'live/ledger.json');outer.assertAlmostEqual(ledger['used_or_reserved_cny'],run017.bound(j))
                    outer.assertEqual(ledger['phases']['headroom']['jobs']['synthetic']['status'],'in_flight')
                    calls.append(job)
                    return dict(http_status=200,body_text='{}',headers={},outcome_unknown=False,started_utc=c.now(),ended_utc=c.now())
            stack.enter_context(patch.object(c.old.NATIVE,'HttpClient',FakeClient))
            stack.enter_context(patch.object(run017,'cost',return_value=(.01,'synthetic_usage')))
            stack.enter_context(patch.object(c.old.old14,'normalize',return_value=dict(status='success')))
            with redirect_stdout(io.StringIO()):run017.run(1,1);run017.run(1,1)
            self.assertEqual(len(calls),1);self.assertAlmostEqual(c.read(out/'live/ledger.json')['used_or_reserved_cny'],.01)
            with redirect_stdout(io.StringIO()),self.assertRaises(ValueError):run017.forecast([j],dict(used_or_reserved_cny=79,phases={}))
            self.assertEqual(len(calls),1)

    def test_failed_headroom_blocks_training_before_data_access(self):
        import learn017
        with patch.object(c,'read',return_value={'passed':False}),patch.object(learn017,'fit') as fit,patch.object(learn017,'logical') as logged:
            with self.assertRaises(ValueError):learn017.learn(Path('unused-synthetic-learning'))
            fit.assert_not_called();logged.assert_not_called()

    def test_pairwise_fit_ignores_other_patient_labels(self):
        import learn017
        a=deepcopy(self.rows[0]);b=deepcopy(a)
        a.update(proposition_id='synthetic_train',subject_id='train')
        b.update(proposition_id='synthetic_selection',subject_id='selection')
        for item in (a,b):
            item['interventions']['c48_local'].update(features_in=[1.]*8,features_out=[0.]*8)
        events=[dict(proposition_id=a['proposition_id'],subject_id='train',arm='c48_local',utility=1),
            dict(proposition_id=b['proposition_id'],subject_id='selection',arm='c48_local',utility=-1)]
        model,provenance=learn017.fit([a,b],events,{'train'})
        events[1]['utility']=1
        again,_=learn017.fit([a,b],events,{'train'})
        self.assertEqual(model,again);self.assertEqual(model['original_pairs'],1)
        self.assertEqual({p['subject_id'] for p in provenance},{'train'})

if __name__=='__main__':unittest.main()
