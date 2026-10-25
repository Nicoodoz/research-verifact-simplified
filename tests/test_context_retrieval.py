"""Offline tests for retrieval scope, text preservation, query construction and budgets."""
from pathlib import Path
import sys
import unittest
import numpy as np
import copy
import json
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tasks/007_context_retrieval"))
import retrieval as r
import prepare as p
import score_results as scoring
from run_judge import RetrievalRunner
from verifact_research.inference.siliconflow_pool import Account
from zero_budget_sensitivity import pack_saved


class RetrievalTests(unittest.TestCase):
    def test_fixed_ceiling_does_not_erase_source_candidates_when_claim_is_empty(self):
        text="Fictional CABG completed with stable recovery."
        corpus=[dict(passage_id="p",search_text=text,text=text,date="2020-01-01",time="Unknown",category="Nursing",note_id="1",start=0,end_exclusive=len(text))]
        primary=r.retrieve(r.BM25(corpus),dict(claim="unmatchedword",sentence="CABG",local="CABG recovery"))
        self.assertEqual(primary["claim"]["matched_character_budget"],0)
        self.assertFalse(primary["sentence"]["passages"])
        restored=pack_saved(corpus,primary["sentence"]["top100"])
        self.assertEqual(restored["passages"][0]["text"],text)
        self.assertFalse(pack_saved(corpus,primary["claim"]["top100"])["passages"])

    def test_four_arm_scoring_blocks_only_incomplete_comparisons(self):
        rows,items,jobs,transports=[],[],[],{}
        for author in ("llm","human"):
            for i,label in enumerate(p.pilot.LABELS):
                pid=f"fake-{author}-{i}"
                rows.append(dict(proposition_id=pid,subject_id=str(i+1),author_type=author,human_gt=label,time_metadata_conflict="False"))
                items.append(dict(proposition_id=pid,case_id=pid,text="Fictional claim",author_type=author,
                    retrieval={arm:dict(reference="1. Date: 2000-01-01 | Text: Fictional EHR.",reference_passage_ids=[],passages=[]) for arm in r.ARMS}))
                for arm in r.ARMS:
                    rid=arm+":"+pid
                    body=dict(model=p.sf.MODEL,messages=[dict(role="user",content=rid)])
                    jobs.append(dict(request_id=rid,body=body,max_cost_cny=.05))
                    answer=dict(verdict=label,reason="Fictional evidence only.",checks=[dict(aspect=a,assessment="Fictional.",evidence_ids=[1]) for a in p.pilot.ASPECTS["structured"]])
                    native=dict(model=p.sf.MODEL,choices=[dict(finish_reason="length" if author=="human" and i==0 and arm=="local" else "stop",message=dict(content=json.dumps(answer)))],usage=dict(prompt_tokens=1000,completion_tokens=100,total_tokens=1100))
                    transports[rid]=dict(http_status=200,body_text=json.dumps(native),headers={},outcome_unknown=False,started_utc="2026-09-14T10:00:00+00:00",ended_utc="2026-09-14T10:00:01+00:00")
        class Client:
            def send(self,account,body):
                return copy.deepcopy(transports[body["messages"][0]["content"]])
        with tempfile.TemporaryDirectory() as tmp, patch("socket.create_connection",side_effect=AssertionError("No network")):
            base=Path(tmp)
            prep=base/"prep"
            prep.mkdir()
            p.pilot.write_csv(prep/"cohort.csv",rows)
            p.pilot.write_jsonl(prep/"inputs.jsonl",items)
            p.pilot.write_json(prep/"manifest.json",{})
            RetrievalRunner([Account("fictional","FICTIONAL-KEY")],jobs,base/"run",16,"fake",client=Client()).run()
            with patch.object(scoring,"load_preparation",return_value=jobs):
                scoring.score(prep,base/"run",base/"analysis")
            metrics=json.loads((base/"analysis/metrics.json").read_text(encoding="utf-8"))
            self.assertEqual(metrics["human"]["contrasts"]["mixed_minus_claim"]["metrics"]["mcc"]["delta"],0)
            self.assertEqual(metrics["human"]["contrasts"]["local_minus_claim"]["status"],"blocked_incomplete_pair")
            self.assertEqual(metrics["llm"]["metrics"]["local"]["mcc"],1)

    def test_registered_unknown_is_not_resent_and_budget_is_retained(self):
        calls=[]
        class Client:
            def send(self,account,body):
                calls.append(body)
                return dict(http_status=0 if len(calls)==1 else 200,body_text="" if len(calls)==1 else "{}",outcome_unknown=len(calls)==1,headers={})
        jobs=[dict(request_id=str(i),body=dict(model="fictional",messages=[dict(role="user",content=str(i))]),max_cost_cny=.1) for i in range(3)]
        with tempfile.TemporaryDirectory() as tmp:
            args=([Account("fictional","FICTIONAL-KEY")],jobs,Path(tmp)/"run",1,"fictional-prep")
            first=RetrievalRunner(*args,client=Client())
            self.assertEqual(first.run()["completed"],0)
            terminal={"0":copy.deepcopy(first.state["jobs"]["0"])}
            with self.assertRaisesRegex(ValueError,"Unregistered"):
                RetrievalRunner(*args,client=Client()).run()
            resumed=RetrievalRunner(*args,client=Client(),terminal_unknown=terminal)
            self.assertEqual(resumed.run()["completed"],2)
            self.assertEqual(len(calls),3)
            self.assertEqual(resumed.state["jobs"]["0"],terminal["0"])
            self.assertAlmostEqual(resumed.state["reserved_budget_cny"],.3)

    def test_spans_preserve_final_paragraph_and_all_nonwhite_characters(self):
        import re
        text="  First paragraph.\n\n"+"Long repeated finding. "*1000+"\n\nFinal paragraph.\n"
        spans=list(r.spans(text))
        self.assertTrue(all(0<b-a<=640 for a,b in spans))
        self.assertEqual(re.sub(r"\s","",text),re.sub(r"\s","","".join(text[a:b] for a,b in spans)))
        self.assertEqual(text[spans[-1][0]:spans[-1][1]],"Final paragraph.")

    def test_sentence_choice_is_literal_and_independent_of_order(self):
        sentences=[dict(text="She received aspirin."),dict(text="She developed fever.")]
        parent="She received aspirin. She developed fever."
        expected=r.sentence_query("Aspirin was administered.",parent,sentences)
        self.assertEqual(expected[0],sentences[0]["text"])
        self.assertEqual(expected,r.sentence_query("Aspirin was administered.",parent,list(reversed(sentences))))

    def test_patient_and_calendar_filter_prevents_cross_patient_and_future_notes(self):
        base=dict(ROW_ID="1",SUBJECT_ID="p1",HADM_ID="a1",CHARTDATE="2020-01-01",CHARTTIME="",CATEGORY="Nursing",DESCRIPTION="Note",TEXT="Fictional EHR.")
        notes=[base,dict(base,ROW_ID="2",SUBJECT_ID="p2"),dict(base,ROW_ID="3",CHARTDATE="2020-02-01"),dict(base,ROW_ID="4",CATEGORY="Discharge summary")]
        # Real IDs are numeric; the helper normalizes them strictly.
        for n in notes:
            n["SUBJECT_ID"]="2" if n["SUBJECT_ID"]=="p2" else "1"
        corpora,excluded=p.corpus_for({"1"},{"1":dict(ADMITTIME="2020-01-01",DISCHTIME="2020-01-03")},notes)
        self.assertEqual({x["note_id"] for x in corpora["1"]},{"1"})
        self.assertEqual(len(excluded),2)

    def test_bm25_known_term_outweighs_unrelated_and_repeat_query_is_invariant(self):
        data=[dict(passage_id=str(i),search_text=text) for i,text in enumerate(("aspirin aspirin fever", "unrelated surgery", "fever infection"))]
        bm=r.BM25(data)
        self.assertEqual(bm.rank("aspirin")[0][0],0)
        self.assertEqual(bm.rank("aspirin"),bm.rank("aspirin aspirin"))
        self.assertEqual(bm.rank("xyzabsent"),[])

    def test_packing_equalizes_budget_and_retains_raw_substrings(self):
        data=[]
        for i in range(40):
            text=("aspirin fever " if i<12 else "surgery catheter ")*(10+i)
            data.append(dict(passage_id=str(i),search_text=text,text=text,date="2020-01-01",time="Unknown",category="Nursing",note_id=str(i),start=0,end_exclusive=len(text)))
        results=r.retrieve(r.BM25(data),dict(claim="aspirin",sentence="aspirin surgery",local="fever catheter surgery"),budget=1500)
        sizes=[v["retrieved_characters"] for v in results.values()]
        self.assertLessEqual(max(sizes),1500)
        self.assertLess(max(sizes)-min(sizes),200)
        for v in results.values():
            for x in v["passages"]:
                original=data[int(x["passage_id"])]
                self.assertEqual(x["text"],original["text"][:x["end_exclusive"]])


if __name__=="__main__":
    unittest.main()
