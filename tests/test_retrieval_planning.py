"""Fictional offline tests for 008's planning isolation, retrieval and native receipts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import planning_core as pc
import services as sv
import common as c
from verifact_research.inference.siliconflow_pool import Account


def transport(kind="chat",status=200):
    body=dict(model=c.CHAT_MODEL,choices=[dict(message=dict(content='{"answer":"fictional"}'),finish_reason="stop")],usage=dict(prompt_tokens=500,completion_tokens=100,total_tokens=600))
    if kind=="embedding":
        body=dict(model=c.EMBED_MODEL,data=[dict(index=0,embedding=[.1,.2])],usage=dict(prompt_tokens=500,total_tokens=500))
    if kind=="rerank":
        body=dict(results=[dict(index=0,relevance_score=.8)],meta=dict(tokens=dict(input_tokens=500)))
    if status==402:
        body=dict(code=30001,message="Balance insufficient",data=None)
    return dict(http_status=status,body_text=json.dumps(body),headers={},outcome_unknown=False,
        started_utc="2026-09-14T14:00:00+00:00",ended_utc="2026-09-14T14:00:01+00:00")


class PlanningTests(unittest.TestCase):
    def setUp(self):
        for name in ("socket.create_connection","socket.socket.connect","socket.socket.connect_ex"):
            guard=patch(name,side_effect=AssertionError("Network disabled"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_terminology_normalization_and_negation(self):
        self.assertEqual(pc.tokenize("post-bypass"),pc.tokenize("POSTBYPASS"))
        self.assertIn("not",pc.tokenize("It was not performed."))
        self.assertNotIn("lastname",pc.tokenize("[CLINICAL_LITERAL_REMOVED]"))

    def test_source_never_redefines_claim_and_quote_validation(self):
        item=dict(text="A procedure occurred.",source=dict(local="On day 5 a procedure occurred."))
        plan=dict(evidence_needs=["Find procedure occurrence."],source_clues=[dict(quote="On day 5",use="soft date clue, not required")],terminology=[],queries=["procedure performed cancelled"],uncertainties=[])
        self.assertEqual(pc.parse_plan(json.dumps(plan),item)["queries"],["procedure performed cancelled"])
        plan["source_clues"][0]["quote"]="On day 9"
        with self.assertRaisesRegex(ValueError,"Unverifiable"):
            pc.parse_plan(json.dumps(plan),item)

    def test_dense_retrieval_rescues_zero_lexical_query(self):
        spans=[dict(passage_id="a",search_text="fictional graft"),dict(passage_id="b",search_text="fictional catheter")]
        index=pc.HybridIndex(spans,[[1,0],[0,1]])
        result=index.retrieve("unseenword",[1,0])
        self.assertEqual(result["bm25"],[])
        self.assertEqual(result["hybrid"][0],"a")

    def test_candidate_cap_and_direct_reservation(self):
        direct=["a"+str(i) for i in range(80)]
        extra=["b"+str(i) for i in range(80)]
        result=pc.candidate_pool([direct,extra],cap=48,reserve_direct=8)
        self.assertEqual(len(result),48)
        self.assertTrue(set(direct[:8])<=set(result))
        self.assertTrue(any(x.startswith("b") for x in result))

    def test_selector_does_not_truncate_hit_or_zero_other_arms(self):
        passages={str(i):dict(note_id=str(i),date="2000-01-01",time="Unknown",category="Note",start=0,end_exclusive=200,text="X"*180+" KEY_HIT_REMAINS.") for i in range(3)}
        result=pc.select_evidence(list(passages),{str(i):3-i for i in range(3)},passages,dict(ADMITTIME="2000-01-01",DISCHTIME="2000-01-02"),cap=500)
        self.assertEqual(len(result["selected_ids"]),1)
        self.assertIn("KEY_HIT_REMAINS",result["reference"])
        empty=pc.select_evidence([],{},passages,dict(ADMITTIME="2000-01-01",DISCHTIME="2000-01-02"))
        self.assertIn("No Electronic",empty["reference"])
        self.assertTrue(result["selected_ids"])

    def test_native_usage_and_fixed_phase_allocation(self):
        self.assertEqual(sum(c.PHASE_CAPS.values()),40)
        for kind in ("embedding","rerank"):
            job=dict(kind=kind,body={})
            self.assertAlmostEqual(sv.cost(job,transport(kind))[0],.000035)

    def test_saved_answers_no_resend_and_balance_rotation(self):
        calls=[]
        class Client:
            def send(self,account,job):
                calls.append(account.alias)
                return transport(status=402 if account.alias=="one" else 200)
        jobs=[dict(request_id="f",kind="chat",body=dict(model=c.CHAT_MODEL,messages=[dict(role="user",content="fictional")],max_tokens=500))]
        with tempfile.TemporaryDirectory() as tmp:
            args=(jobs,Path(tmp)/"run","planner",[Account("one","FICTIONAL-ONE"),Account("two","FICTIONAL-TWO")])
            first=sv.NativeRunner(*args,client=Client())
            self.assertTrue(first.run(1)["complete"])
            self.assertEqual(calls,["one","two"])
            self.assertAlmostEqual(first.state["used_or_reserved_cny"],.0024)
            self.assertTrue(sv.NativeRunner(*args,client=Client()).run(1)["complete"])
            self.assertEqual(len(calls),2)

    def test_crash_after_receipt_recovers_without_resend(self):
        calls=[]
        class Client:
            def send(self,account,job):
                calls.append(job)
                return transport()
        jobs=[dict(request_id="f",kind="chat",body=dict(model=c.CHAT_MODEL,messages=[dict(role="user",content="fictional")],max_tokens=500))]
        with tempfile.TemporaryDirectory() as tmp:
            args=(jobs,Path(tmp)/"run","planner",[Account("one","FICTIONAL-ONE")])
            first=sv.NativeRunner(*args,client=Client())
            with patch.object(first,"_finish",side_effect=RuntimeError("fictional interruption")):
                with self.assertRaises(RuntimeError):
                    first.run(1)
            self.assertTrue(sv.NativeRunner(*args,client=Client()).run(1)["complete"])
            self.assertEqual(len(calls),1)

    def test_unknown_response_pauses_without_retry(self):
        calls=[]
        class Client:
            def send(self,account,job):
                calls.append(job)
                return dict(http_status=0,body_text="",headers={},outcome_unknown=True)
        jobs=[dict(request_id=str(i),kind="chat",body=dict(model=c.CHAT_MODEL,messages=[dict(role="user",content="fictional")],max_tokens=500)) for i in range(2)]
        with tempfile.TemporaryDirectory() as tmp:
            runner=sv.NativeRunner(jobs,Path(tmp)/"run","planner",[Account("one","FICTIONAL")],client=Client())
            self.assertEqual(runner.run(1)["pause_reason"],"unknown")
            self.assertEqual(len(calls),1)
            self.assertAlmostEqual(runner.state["used_or_reserved_cny"],sv.bound(jobs[0]))


if __name__=="__main__":
    unittest.main()
