from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from contextlib import ExitStack,redirect_stdout
from types import SimpleNamespace
import tempfile
import io
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tasks/016_disagreement_triggered_review_validation'))
import common016 as c
from decisions016 import compose,select_limited
from run016 import next_status,execute

class ReviewValidationTests(unittest.TestCase):
    def rows(self):
        return [dict(proposition_id=str(i),subject_id=str(i//6),author_type='human' if i%2 else 'llm',human_gt='Supported',
            v4_first='Supported',qwen='Not Addressed' if i%3==0 else 'Supported',v4_repeat='Not Supported' if i%4==0 else 'Supported',
            independent_review='Not Supported') for i in range(24)]

    def test_trigger_and_hash_do_not_depend_on_GT(self):
        a=compose(self.rows());b=compose([dict(r,human_gt='Not Addressed') for r in self.rows()])
        for left,right in zip(a,b):
            for key in ('cross_trigger','hash_trigger','self_trigger','cross_review','cross_repeat','hash_review'):self.assertEqual(left[key],right[key])

    def test_hash_exactly_matches_per_patient_author_counts(self):
        rows=compose(self.rows())
        for sid in {r['subject_id'] for r in rows}:
            for author in ('llm','human'):
                rr=[r for r in rows if r['subject_id']==sid and r['author_type']==author]
                self.assertEqual(sum(r['cross_trigger'] for r in rr),sum(r['hash_trigger'] for r in rr))

    def test_agreement_preserved_and_second_repeat_distinct(self):
        rows=compose(self.rows())
        self.assertTrue(all(r['cross_review']==r['v4_first'] for r in rows if not r['cross_trigger']))
        self.assertTrue(any(r['cross_review']!=r['cross_repeat'] for r in rows if r['cross_trigger']))

    def test_union_not_constructed_until_allowed(self):
        self.assertTrue(all('union_review' not in r for r in compose(self.rows())))
        rows=compose(self.rows(),union=True)
        self.assertTrue(all(r['union_trigger']==(r['cross_trigger'] or r['self_trigger']) for r in rows))
        with self.assertRaises(ValueError):select_limited([],{},dict(passed=False))

    def test_no_successful_200_regeneration(self):
        self.assertEqual(next_status(dict(http_status=200,body_text='truncated'),1,0,0),'received')
        self.assertEqual(next_status(dict(http_status=0,body_text=''),2,2,0),'failed_unknown')

    def test_fixed_role_bodies(self):
        prompts=c.read(c.ROOT/'outputs/009_retrieval_baselines/confirmation_001/preparation/judge_prompts.json')
        item=dict(text='A synthetic claim.',proposition_id='synthetic')
        v1=c.judge_body(item,'1. synthetic reference',prompts,'v4_first')
        v2=c.judge_body(item,'1. synthetic reference',prompts,'v4_repeat')
        q=c.judge_body(item,'1. synthetic reference',prompts,'qwen')
        review=c.judge_body(item,'1. synthetic reference',prompts,'independent_review')
        self.assertEqual(v1,v2);q['model']=c.V4;self.assertEqual(v1,q)
        self.assertEqual(review,c.old15.build_body(v1,'synthetic','','','evidence_only'))
        self.assertEqual(set(c.pilot.strict_json(review['messages'][1]['content'])),{'proposition','reference'})

    def test_one_budget_across_phases_without_real_calls(self):
        calls=[]
        class FakeClient:
            def send(self,account,job):
                calls.append(job['request_id'])
                return dict(http_status=200,body_text='{}',started_utc=c.now(),ended_utc=c.now())
        with tempfile.TemporaryDirectory(prefix='verifact016-budget-') as temp,ExitStack() as stack:
            root=Path(temp);out=root/'task';out.mkdir()
            c.write_json(out/'authority_001.json',dict(approved=True,task_cap_cny=.1,execution_sha256={},synthetic_test_only=True))
            paths=[]
            for kind,model in [('embedding',c.baseline.EMBED_MODEL),('rerank',c.baseline.RERANK_MODEL)]:
                p=out/'stage1'/kind;p.mkdir(parents=True)
                c.write_lines(p/'jobs.jsonl',[dict(request_id=kind,kind=kind,body=dict(model=model))])
                c.write_json(p/'manifest.json',{});paths.append(p/'jobs.jsonl')
            stack.enter_context(patch.object(c,'ROOT',root));stack.enter_context(patch.object(c,'OUT',out))
            stack.enter_context(patch.object(c,'patient_ids',return_value=[]));stack.enter_context(patch.object(c,'check_manifest',return_value={}))
            stack.enter_context(patch.object(c,'load_accounts',return_value=[SimpleNamespace(alias='account_2',key='synthetic-test-key')]))
            stack.enter_context(patch.object(c.NATIVE,'HttpClient',FakeClient))
            stack.enter_context(patch.object(c,'bound',side_effect=lambda j:.06 if j['kind']=='embedding' else .08))
            stack.enter_context(patch.object(c,'cost',return_value=(.04,'synthetic_usage')))
            with redirect_stdout(io.StringIO()):
                execute(paths[0],workers=1);execute(paths[1],workers=1)
            ledger=c.read(out/'live/ledger.json')
            self.assertEqual(calls,['embedding'])
            self.assertAlmostEqual(ledger['used_or_reserved_cny'],.04)
            self.assertTrue(c.read(out/'live/stage1_rerank/summary.json')['budget_halt'])

if __name__=='__main__':unittest.main()
