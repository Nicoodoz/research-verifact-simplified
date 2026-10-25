"""009 offline properties and failure recovery; all clients are fictional."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tasks/009_retrieval_baselines"))
import study009 as s
from native_stage import StageRunner
from verifact_research.inference.siliconflow_pool import Account


def job(rid="one"):
    return dict(request_id=rid,kind="chat",body=dict(model=s.CHAT_MODEL,messages=[dict(role="user",content="fictional")],max_tokens=500))


def transport(status=200):
    body=dict(model=s.CHAT_MODEL,choices=[dict(message=dict(content="{}"),finish_reason="stop")],usage=dict(prompt_tokens=500,completion_tokens=100,total_tokens=600))
    if status==402:
        body=dict(code=30001,message="Balance insufficient",data=None)
    if status==503:
        body=dict(error="fictional unavailable")
    return dict(http_status=status,body_text=json.dumps(body) if status else "",outcome_unknown=status==0,headers={},
        started_utc="2026-09-15T12:00:00+00:00",ended_utc="2026-09-15T12:00:01+00:00")


class BaselineTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.create_connection","socket.socket.connect","socket.socket.connect_ex"):
            guard=patch(target,side_effect=AssertionError("Network prohibited"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_quota_preserves_each_route_and_capacity_with_overlap(self):
        dense=[str(i) for i in range(80)]
        lexical=[str(i) for i in range(10,90)]
        result=s.quota_candidates(dense,lexical)
        self.assertEqual(len(result),48)
        self.assertTrue(set(dense[:24])<=set(result))
        self.assertTrue(set(lexical[:24])<=set(result))
        self.assertEqual(s.quota_candidates(dense,[]),dense[:48])

    def test_whitespace_recovery_does_not_modify_queries_or_accept_false_content(self):
        item=dict(source=dict(local="The procedure\nwas done."))
        value=dict(evidence_needs=["occurrence"],source_clues=[dict(quote="The procedure was done.",use="unverified clue")],terminology=[],queries=["procedure status"],uncertainties=[])
        self.assertEqual(s.relaxed_plan(json.dumps(value),item),value)
        value["source_clues"][0]["quote"]="The procedure was cancelled."
        with self.assertRaises(ValueError):
            s.relaxed_plan(json.dumps(value),item)
        value["source_clues"]=[]
        value["extra"]="not silently discarded"
        with self.assertRaises(ValueError):
            s.relaxed_plan(json.dumps(value),item)

    def test_received_model_answer_is_never_resent_and_manifest_is_bound(self):
        calls=[]
        class Client:
            def send(self,account,request):
                calls.append(request)
                return transport()
        with tempfile.TemporaryDirectory() as tmp:
            args=("dev_judge",[job()],[Account("one","FICTIONAL_KEY")])
            runner=StageRunner(*args,client=Client(),output=tmp)
            self.assertTrue(runner.run(1,0)["complete"])
            self.assertTrue(StageRunner(*args,client=Client(),output=tmp).run(1,0)["complete"])
            self.assertEqual(len(calls),1)
            changed=job()
            changed["body"]["max_tokens"]=501
            with self.assertRaises(ValueError):
                StageRunner("dev_judge",[changed],args[2],client=Client(),output=tmp).run(1,0)

    def test_failed_unknown_keeps_both_reservations_and_continues_other_jobs(self):
        calls=[]
        class Client:
            def send(self,account,request):
                calls.append(request["request_id"])
                return transport(0 if request["request_id"]=="one" else 200)
        with tempfile.TemporaryDirectory() as tmp:
            runner=StageRunner("dev_judge",[job(),job("two")],[Account("one","FICTIONAL_KEY")],client=Client(),output=tmp)
            result=runner.run(1,0)
            self.assertEqual(calls,["one","one","two"])
            self.assertEqual(result["status_counts"],dict(failed_unknown=1,received=1))
            self.assertAlmostEqual(result["used_or_reserved_cny"],2*s.native.bound(job())+.0024)
            self.assertEqual(len(list(Path(tmp).glob("receipt*.json"))),3)

    def test_transient_failure_is_bounded_and_does_not_abandon_unsent(self):
        counts={}
        class Client:
            def send(self,account,request):
                rid=request["request_id"]
                counts[rid]=counts.get(rid,0)+1
                return transport(503 if rid=="one" else 200)
        with tempfile.TemporaryDirectory() as tmp:
            runner=StageRunner("dev_judge",[job(),job("two")],[Account("one","FICTIONAL_KEY")],client=Client(),output=tmp)
            self.assertEqual(runner.run(1,0)["status_counts"],dict(failed_service=1,received=1))
            self.assertEqual(counts,dict(one=3,two=1))

    def test_saved_receipt_after_interruption_recovers_without_duplicate_call(self):
        calls=[]
        class Client:
            def send(self,account,request):
                calls.append(request)
                return transport()
        with tempfile.TemporaryDirectory() as tmp:
            args=("dev_judge",[job()],[Account("one","FICTIONAL_KEY")])
            runner=StageRunner(*args,client=Client(),output=tmp)
            with patch.object(runner,"finish",side_effect=RuntimeError("fictional interruption")):
                with self.assertRaises(RuntimeError):
                    runner.run(1,0)
            self.assertTrue(StageRunner(*args,client=Client(),output=tmp).run(1,0)["complete"])
            self.assertEqual(len(calls),1)

    def test_balance_rotation_preserves_task_stage_budget(self):
        calls=[]
        class Client:
            def send(self,account,request):
                calls.append(account.alias)
                return transport(402 if account.alias=="empty" else 200)
        with tempfile.TemporaryDirectory() as tmp:
            runner=StageRunner("dev_judge",[job()],[Account("empty","FICTIONAL_ONE"),Account("next","FICTIONAL_TWO")],client=Client(),output=tmp)
            self.assertTrue(runner.run(1,0)["complete"])
            self.assertEqual(calls,["empty","next"])
            self.assertAlmostEqual(runner.state["used_or_reserved_cny"],.0024)
            self.assertEqual(sum(s.STAGE_CAPS.values()),40)

    def test_missing_prediction_blocks_only_affected_complete_pair(self):
        from score009 import evaluate_scope
        cohort=[]
        labels=['Supported','Not Supported','Not Addressed']
        for author in ('llm','human'):
            for sid in ('1','2'):
                for i,label in enumerate(labels):
                    cohort.append(dict(proposition_id=author+sid+str(i),subject_id=sid,author_type=author,
                        proposition_type='claim',invalid='False',human_gt=label))
        full=[dict(proposition_id=r['proposition_id'],verdict=r['human_gt']) for r in cohort]
        predictions={'A48':full,'B48':full[1:],'C48':full}
        result=evaluate_scope(cohort,predictions,('A48','B48','C48'),[('A48','B48'),('A48','C48')])
        self.assertEqual(result['llm']['contrasts']['B48_minus_A48']['status'],'blocked_incomplete_pair')
        self.assertNotIn('status',result['llm']['contrasts']['C48_minus_A48'])
        self.assertNotIn('status',result['human']['contrasts']['B48_minus_A48'])
        self.assertEqual(result['llm']['metrics']['B48']['missing_ids'],['llm10'])

    def test_reusable_packer_rejects_uncomputed_scores_and_handles_empty_evidence(self):
        from retrieval_baseline import pack
        admission=dict(ADMITTIME='2000-01-01',DISCHTIME='2000-01-02')
        with self.assertRaisesRegex(ValueError,'Missing real rerank scores'):
            pack(['missing'],{}, {},admission)
        with self.assertRaisesRegex(ValueError,'Nonfinite'):
            pack(['bad'],{'bad':float('nan')},{},admission)
        result=pack([],{}, {},admission)
        self.assertEqual(result['selected_ids'],[])
        self.assertIn('No Electronic Health Record Context Found.',result['reference'])

    def test_stage_cap_stops_before_sending_and_cannot_be_reset_on_resume(self):
        calls=[]
        class Client:
            def send(self,account,request):
                calls.append(request)
                return transport()
        huge=job()
        huge['body']['max_tokens']=1000000
        with tempfile.TemporaryDirectory() as tmp:
            args=('dev_judge',[huge],[Account('one','FICTIONAL_KEY')])
            first=StageRunner(*args,client=Client(),output=tmp).run(1,0)
            second=StageRunner(*args,client=Client(),output=tmp).run(1,0)
            self.assertEqual(first['status_counts'],{'pending':1})
            self.assertEqual(second['used_or_reserved_cny'],0)
            self.assertEqual(calls,[])


if __name__=="__main__":
    unittest.main()
