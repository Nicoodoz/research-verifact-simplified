"""Fictional-data tests for 006 context isolation, budget settlement and scoring."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tasks/006_source_context_feasibility"))
import context_feasibility as cf
import run_context_pilot as execution
import score_context_pilot as scoring
from verifact_research.inference.siliconflow_pool import Account


def fake_transport(verdict="Supported",finish="stop"):
    answer=dict(verdict=verdict,reason="Fictional evidence only.",checks=[dict(aspect=a,assessment="Fictional.",evidence_ids=[1]) for a in cf.pilot.ASPECTS["structured"]])
    native=dict(model=cf.sf.MODEL,choices=[dict(finish_reason=finish,message=dict(content=json.dumps(answer)))],
        usage=dict(prompt_tokens=1000,completion_tokens=100,total_tokens=1100,completion_tokens_details=dict(reasoning_tokens=0)))
    return dict(http_status=200,body_text=json.dumps(native),headers={},outcome_unknown=False,
        started_utc="2026-09-14T10:00:00+00:00",ended_utc="2026-09-14T10:00:01+00:00")


class Client:
    def __init__(self):
        self.calls=[]
    def send(self,account,body):
        self.calls.append((account.alias,body))
        return fake_transport()


class SourceContextFeasibilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        for name in ("socket.socket.connect","socket.socket.connect_ex","socket.create_connection"):
            guard=patch(name,side_effect=AssertionError("Network disabled"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_sampling_is_fixed_balanced_and_not_input_order_dependent(self):
        rows=[]
        for sid in ("p1","p2"):
            for author in ("llm","human"):
                for label in cf.pilot.LABELS:
                    for i in range(20):
                        rows.append(dict(subject_id=sid,author_type=author,human_gt=label,
                            proposition_id=f"{sid}-{author}-{label}-{i}",human_csv_order=str(len(rows))))
        a,b=cf.select(rows,["p1","p2"]),cf.select(list(reversed(rows)),["p1","p2"])
        self.assertEqual(a,b)
        self.assertEqual(len(a),64)
        for sid in ("p1","p2"):
            for author in ("llm","human"):
                part=[r for r in a if r["subject_id"]==sid and r["author_type"]==author]
                self.assertEqual([sum(r["human_gt"]==lab for r in part) for lab in cf.pilot.LABELS],[6,5,5])

    def test_context_is_exact_source_span_and_ambiguous_parent_is_rejected(self):
        prop=dict(parent_text_chunk="Then he improved.",brief_hospital_course="α event first. Then he improved.")
        window=cf.source_window(prop,5)
        self.assertEqual(window["text"],prop["brief_hospital_course"][window["start"]:window["end_exclusive"]])
        prop["brief_hospital_course"]+=" Then he improved."
        with self.assertRaisesRegex(ValueError,"exactly one"):
            cf.source_window(prop)

    def test_only_auxiliary_text_changes_and_gt_is_not_sent(self):
        item=dict(text="Fictional target.",reference="1. Date: 2000 | Text: Fictional EHR.",source_context=dict(text="Fictional source context, not evidence."),human_gt="SECRET_GT")
        prompts=dict(common="Common rules",structured="Five checks")
        calls={a:cf.messages(item,a,prompts) for a in cf.ARMS}
        self.assertEqual(len({c[0]["content"] for c in calls.values()}),1)
        bodies={a:json.loads(c[1]["content"]) for a,c in calls.items()}
        self.assertEqual({b["reference"] for b in bodies.values()},{item["reference"]})
        self.assertEqual({b["proposition"] for b in bodies.values()},{item["text"]})
        self.assertNotIn("SECRET_GT",json.dumps(calls))
        self.assertEqual(bodies["structured"]["unverified_source_text"],"")
        self.assertEqual(bodies["source_context"]["unverified_source_text"],item["source_context"]["text"])

    def test_repeat_control_keeps_whole_claim_and_scope_flags_do_not_claim_equivalence(self):
        claim="A fictional claim."
        text=cf.repeated_claim(claim,150)
        self.assertTrue(all(line==claim for line in text.splitlines()))
        self.assertLessEqual(abs(len(text)-150),len(claim)+1)
        flags=cf.context_flags(claim,"At 100 mg on day 6. "+claim)
        self.assertEqual(flags["additional_number_strings"],["100","6"])
        self.assertTrue(flags["context_not_proven_semantically_equivalent"])

    def test_meter_releases_unused_reservation_without_resetting_total_budget(self):
        client=Client()
        jobs=[dict(request_id=f"f{i}",body=dict(model=cf.sf.MODEL,messages=[dict(role="user",content="fictional")]),max_cost_cny=.05) for i in range(5)]
        runner=execution.MeteredRunner([Account("fictional","FICTIONAL-KEY")],jobs,self.root/"run",.1,"fictional-prep",client=client)
        result=runner.run()
        self.assertEqual(result["completed"],5)
        self.assertAlmostEqual(result["reserved_budget_cny"],5*.0039)
        again=execution.MeteredRunner([Account("fictional","FICTIONAL-KEY")],jobs,self.root/"run",.1,"fictional-prep",client=client)
        self.assertEqual(again.run()["completed"],5)
        self.assertEqual(len(client.calls),5)

    def test_meter_recovers_saved_response_without_duplicate_send_or_double_settlement(self):
        client=Client()
        jobs=[dict(request_id="f",body=dict(model=cf.sf.MODEL,messages=[dict(role="user",content="fictional")]),max_cost_cny=.05)]
        runner=execution.MeteredRunner([Account("fictional","FICTIONAL-KEY")],jobs,self.root/"run",.1,"fictional-prep",client=client)
        with patch.object(runner,"_finish",side_effect=RuntimeError("fictional interruption")):
            with self.assertRaises(RuntimeError):
                runner.run()
        result=execution.MeteredRunner([Account("fictional","FICTIONAL-KEY")],jobs,self.root/"run",.1,"fictional-prep",client=client).run()
        self.assertEqual(len(client.calls),1)
        self.assertAlmostEqual(result["reserved_budget_cny"],.0039)

    def test_context_arm_uses_same_parser_and_truncation_is_still_failure(self):
        job=dict(request_id="source_context:fictional-p",body=dict(model=cf.sf.MODEL))
        item=dict(reference="1. Date: 2000 | Text: Fictional EHR.")
        normal=scoring.normalize(job,item,fake_transport())
        self.assertEqual(normal["arm"],"source_context")
        self.assertEqual(normal["status"],"success")
        self.assertEqual(scoring.normalize(job,item,fake_transport(finish="length"))["status"],"failed")

    def test_no_execution_or_secret_loading_without_matching_approval(self):
        auth=self.root/"authorization.json"
        auth.write_text('{"approved":false}',encoding="utf-8")
        with patch.object(execution,"load_preparation",return_value=[]),patch.object(execution,"load_accounts",side_effect=AssertionError("No credential loading")):
            with self.assertRaisesRegex(ValueError,"No approval"):
                execution.execute(self.root,self.root/"run",auth)

    def test_offline_end_to_end_scoring_uses_complete_pairs_and_does_not_impute_truncation(self):
        prep=self.root/"prep"
        prep.mkdir()
        cohort,inputs,jobs,answers=[],[],[],{}
        for author in ("llm","human"):
            for i,truth in enumerate(cf.pilot.LABELS):
                pid=f"fictional-{author}-{i}"
                cohort.append(dict(proposition_id=pid,subject_id=f"p{i}",author_type=author,human_gt=truth))
                inputs.append(dict(proposition_id=pid,reference="1. Date: 2000 | Text: Fictional evidence."))
                for arm in cf.ARMS:
                    content=pid+"|"+arm
                    jobs.append(dict(request_id=arm+":"+pid,body=dict(model=cf.sf.MODEL,messages=[dict(role="user",content=content)]),max_cost_cny=.05))
                    answers[content]=fake_transport(truth if arm=="source_context" else "Supported",
                        finish="length" if author=="llm" and i==0 and arm=="source_context" else "stop")
        class FakeClient:
            def send(self,account,body):
                return copy.deepcopy(answers[body["messages"][0]["content"]])
        cf.pilot.write_csv(prep/"cohort.csv",cohort)
        cf.pilot.write_jsonl(prep/"inputs.jsonl",inputs)
        cf.pilot.write_json(prep/"manifest.json",{})
        run=self.root/"run"
        execution.MeteredRunner([Account("fictional","FICTIONAL-KEY")],jobs,run,8,"fictional-prep",client=FakeClient()).run()
        with patch.object(scoring,"load_preparation",return_value=jobs):
            scoring.score(prep,run,self.root/"analysis")
        metrics=json.loads((self.root/"analysis/metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(metrics["human"]["metrics"]["source_context"]["mcc"],1)
        self.assertEqual(metrics["human"]["contrasts"]["source_context_minus_structured"]["metrics"]["mcc"]["delta"],1)
        self.assertEqual(metrics["llm"]["metrics"]["source_context"]["expected_n"],3)
        self.assertEqual(metrics["llm"]["contrasts"]["source_context_minus_structured"]["status"],"blocked_incomplete_pair")


if __name__=="__main__":
    unittest.main()
