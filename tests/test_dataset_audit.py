"""Synthetic regression tests: no clinical data or network required."""

import copy
import sys
import tempfile
import unittest
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifact_research.audit.ai import audit_ai, classify_reference_header, expected_configurations
from verifact_research.audit.cohort import audit_cohort, key_audit
from verifact_research.audit.common import (Checks, csv_profile, integer_id,
                                           digest_text, literal_positions, majority, new_run)
from verifact_research.audit.release import parse_checksums


def fixture():
    tables = {name:[] for name in ("propositions","human_verdicts","proposition_validity",
                                   "ehr_noteevents","admissions","model_metadata","rater_configurations")}
    for author in ("human", "llm"):
        for kind in ("claim", "sentence"):
            pid = author+"-"+kind
            tables["propositions"].append({"proposition_id":pid,"text":"Alpha.","parent_text_chunk":"Alpha.",
                                           "brief_hospital_course":"Alpha.","subject_id":"1","hadm_id":"10",
                                           "row_id":"100.0" if author=="human" else "", "author_type":author,
                                           "proposition_type":kind,"admitdate":"2020-01-01","admittime":"00:00:00",
                                           "dischargedate":"2020-01-02","dischargetime":"12:00:00"})
            g = {"proposition_id":pid,"text":"Alpha.","author_type":author,"proposition_type":kind,
                 "human_gt":"Supported","round1_num_raters_agree":"3","round1_majority_vote":"Supported",
                 "round2_decision":"","adjudicated_verdict":"","adjudicated_comment":""}
            for n in range(1,6):
                g.update({f"rater{n}":f"doctor{n}" if n<=3 else "",f"verdict{n}":"Supported" if n<=3 else "",f"comment{n}":""})
                if n<=3:
                    g[f"uncertain_flag{n}"]="False"
            tables["human_verdicts"].append(g)
            v = {"proposition_id":pid,"text":"Alpha.","author_type":author,"proposition_type":kind,"invalid":"False"}
            for name in ("imperative","interrogative","incomplete","vague"):
                v[name]=v[name+"_draft"]="False"
            tables["proposition_validity"].append(v)
    tables["admissions"] = [{"ROW_ID":"1","SUBJECT_ID":"1","HADM_ID":"10","ADMITTIME":"2020-01-01 00:00:00","DISCHTIME":"2020-01-02 12:00:00"}]
    tables["ehr_noteevents"] = [{"ROW_ID":"2","SUBJECT_ID":"1","HADM_ID":"10.0","CHARTDATE":"2020-01-01",
                                 "CHARTTIME":"2020-01-01 01:00:00","STORETIME":"2020-01-01 02:00:00",
                                 "CATEGORY":"Physician","DESCRIPTION":"test","TEXT":"Alpha."}]
    return tables


class AuditHelpersTest(unittest.TestCase):
    def test_ids_preserve_integer_precision_and_reject_fraction(self):
        self.assertEqual(integer_id("183959.0"), "183959")
        self.assertEqual(integer_id("9007199254740993.0"), "9007199254740993")
        self.assertIsNone(integer_id(""))
        for text in ("1.5", "NaN", "inf", "x"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                integer_id(text)

    def test_three_way_tie_is_not_a_majority(self):
        self.assertEqual(majority(["Supported","Not Supported","Not Addressed"]),(0,None))
        self.assertEqual(majority(["Not Addressed","Supported","Not Addressed"]),(2,"Not Addressed"))
        with self.assertRaises(ValueError):
            majority(["Supported", "Supported", "unknown"])

    def test_duplicate_text_does_not_receive_a_false_unique_offset(self):
        self.assertEqual(literal_positions("A. A.","A."),[0,3])
        self.assertEqual(literal_positions("aaaa","aa"),[0,1,2])
        self.assertEqual(literal_positions("A.",""),[])

    def test_missingness_distinguishes_empty_and_whitespace(self):
        col=csv_profile(["x"],[{"x":""},{"x":" "},{"x":"False"}])["columns"][0]
        self.assertEqual((col["empty_count"],col["whitespace_only_count"],col["null_count"]),(1,1,0))

    def test_manifest_rejects_duplicate_and_traversal_paths(self):
        h="a"*64
        self.assertEqual(parse_checksums(h+"  folder/a b.txt\n"),{"folder/a b.txt":h})
        for text in (h+" ../outside\n", h+" a\n"+h+" a\n"):
            with self.assertRaises(ValueError):
                parse_checksums(text)

    def test_output_never_overwrites_run_or_targets_raw(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            raw=root/"raw"
            raw.mkdir()
            self.assertEqual(new_run(root/"out",None,raw).name,"run_001")
            self.assertEqual(new_run(root/"out",None,raw).name,"run_002")
            with self.assertRaises(FileExistsError):
                new_run(root/"out","run_001",raw)
            with self.assertRaises(ValueError):
                new_run(raw/"nested",None,raw)
            with self.assertRaises(ValueError):
                new_run(root/"out","../escape",raw)

    def test_duplicate_primary_key_is_detected(self):
        checks=Checks()
        key_audit([{"id":"a"},{"id":"a"}],"id","synthetic",checks)
        self.assertTrue(checks.failed)


class CoverageTest(unittest.TestCase):
    def test_reference_header_comparison_respects_configuration_format(self):
        metadata = {'proposition_admittime':'2020-01-01 00:00:00', 'proposition_dischtime':'2020-01-02 12:00:00',
                    'admissions_admittime':'2020-01-01 00:00:00', 'admissions_dischtime':'2020-01-02 12:00:00'}
        for format_name, start, end, status in (
            ('relative_time', '1 days 12 hours ago', 'Now', 'relative_time_not_compared'),
            ('score', '', '', 'score_not_applicable'),
            ('absolute_time', '', '', 'unparseable_absolute'),
            ('absolute_time', '1 days 12 hours ago', 'Now', 'unparseable_absolute'),
            ('unexpected_format', '', '', 'unknown_reference_format'),
        ):
            with self.subTest(format_name=format_name, start=start):
                result = classify_reference_header({**metadata, 'reference_format':format_name,
                                                    'reference_start':start, 'reference_end':end})
                self.assertEqual(result['comparison_status'], status)
                self.assertIsNone(result['matches_admissions'])
                self.assertIsNone(result['matches_propositions'])
        absolute = classify_reference_header({**metadata, 'reference_format':'absolute_time',
                                               'reference_start':'2020-01-01T00:00:00',
                                               'reference_end':'2020-01-02 12:00:00'})
        self.assertTrue(absolute['matches_admissions'])
        self.assertEqual(absolute['comparison_status'], 'compared_absolute')

    def test_rater_is_shared_across_strata_and_preliminary_models_are_restricted(self):
        config={"fact_type":"sentence","retrieval_method":"rerank","top_n":"100",
                "reference_format":"absolute_time","reference_only_admission":"True","deduplicate_text":"True"}
        raters=[{"model":model,"rater_alias":model,**config} for model in ("R1-70B","Gemma-3-12B")]
        matrix=[{"author_type":author,"proposition_type":"claim","publication_role":"main",**config} for author in ("human","llm")]
        pairs, errors=expected_configurations(raters,matrix,["R1-70B","Gemma-3-12B"])
        self.assertFalse(errors)
        self.assertEqual(len(pairs),4)
        self.assertEqual(len({r["rater_alias"] for r in pairs}),2)
        preliminary=[{**matrix[0],"publication_role":"preliminary_sensitivity"}]
        pairs,errors=expected_configurations(raters,preliminary,["R1-70B","Gemma-3-12B"])
        self.assertEqual([r["model"] for r in pairs],["R1-70B"])
        pairs,errors=expected_configurations([],matrix,["R1-70B"])
        self.assertEqual(len(errors),2)


class CohortTest(unittest.TestCase):
    def test_later_clinicians_agree_but_final_label_is_changed(self):
        tables = fixture()
        row = tables['human_verdicts'][0]
        row.update(verdict1='Supported', verdict2='Not Supported', verdict3='Not Addressed',
                   round1_num_raters_agree='0', round1_majority_vote='',
                   rater4='doctor4', rater5='doctor5', verdict4='Not Supported', verdict5='Not Supported',
                   round2_decision='Agree', adjudicated_verdict='Not Supported', human_gt='Not Supported')
        checks = Checks()
        audit_cohort(tables, ['1'], checks)
        self.assertFalse(checks.failed)
        # A self-consistent final/adjudicated label must still agree with the two later votes.
        row.update(adjudicated_verdict='Supported', human_gt='Supported')
        checks = Checks()
        audit_cohort(tables, ['1'], checks)
        self.assertEqual(next(r['status'] for r in checks.rows if r['id']=='human.second_round_consistency'), 'fail')
        # Agree cannot be reconstructed from two saved, unequal individual votes.
        row.update(verdict5='Supported', adjudicated_verdict='Supported', human_gt='Supported')
        checks = Checks()
        summary, exports, _ = audit_cohort(tables, ['1'], checks)
        self.assertEqual(next(r['status'] for r in checks.rows if r['id']=='human.second_round_consistency'), 'fail')
        self.assertEqual(summary['second_round_votes_different'], 1)
        self.assertEqual(exports['second_round_anomalies'][0]['verdict4'], 'Not Supported')

    def test_synthetic_cohort_and_wrong_ground_truth(self):
        tables=fixture()
        checks=Checks()
        summary,exports,_=audit_cohort(tables,["1"],checks)
        self.assertFalse(checks.failed)
        self.assertEqual((summary["propositions"],summary["documents"],summary["patients"]),(4,2,1))
        self.assertEqual(summary["human_gt"],{"Supported":4})
        broken=copy.deepcopy(tables)
        broken["human_verdicts"][0]["human_gt"]="Not Supported"
        checks=Checks()
        audit_cohort(broken,["1"],checks)
        self.assertEqual(next(r["status"] for r in checks.rows if r["id"]=="human.majority_and_adjudication"),"fail")

    def test_missing_annotation_cannot_silently_disappear_in_a_join(self):
        tables=fixture()
        tables["human_verdicts"].pop()
        checks=Checks()
        with self.assertRaises(ValueError):
            audit_cohort(tables,["1"],checks)
        self.assertTrue(checks.failed)

    def test_final_validity_union_and_draft_are_separate(self):
        tables=fixture()
        tables["proposition_validity"][0]["vague_draft"]="True"
        checks=Checks()
        summary,_,_=audit_cohort(tables,["1"],checks)
        self.assertFalse(checks.failed)
        self.assertEqual(summary["validity"]["invalid"],0)
        tables["proposition_validity"][0]["vague"]="True"
        checks=Checks()
        audit_cohort(tables,["1"],checks)
        self.assertEqual(next(r["status"] for r in checks.rows if r["id"]=="validity.final_union"),"fail")

    def test_conflicting_discharge_dates_are_reported_without_changing_identity(self):
        tables=fixture()
        for row in tables["propositions"]:
            if row["author_type"]=="llm":
                row["dischargedate"]="2020-01-03"
        checks=Checks()
        summary,exports,joined=audit_cohort(tables,["1"],checks)
        self.assertFalse(checks.failed)
        self.assertEqual(len(exports["admission_metadata_conflicts"]),2)
        self.assertEqual(summary["admission_metadata_conflicts"][0]["difference_seconds"],86400)
        self.assertEqual(next(r["status"] for r in checks.rows if r["id"]=="admissions.timestamp_metadata_agreement"),"warning")
        self.assertTrue(any(r["proposition_dischtime"]!=r["admissions_dischtime"] for r in joined))


class ParquetAuditTest(unittest.TestCase):
    def test_missing_prediction_and_changed_judge_context_are_independent(self):
        config={"fact_type":"sentence","retrieval_method":"rerank","top_n":"100",
                "reference_format":"absolute_time","reference_only_admission":"True","deduplicate_text":"True"}
        models=[{"model":name,"source_artifact":"synthetic.feather","source_sha256":"a"*64} for name in ("R1-70B","Gemma-3-12B")]
        raters=[]
        for model in models:
            row={"model":model["model"],"rater_alias":model["model"],**config}
            row["rater_name"]="model="+row["model"]+","+",".join(f"{k}={v}" for k,v in config.items())
            raters.append(row)
        matrix=[{"author_type":a,"proposition_type":"claim","publication_role":"main",**config} for a in ("human","llm")]
        propositions=[{"proposition_id":a,"subject_id":"1","hadm_id":"10","author_type":a,
                       "proposition_type":"claim","human_gt":"Supported","invalid":False,
                       "proposition_admittime":"2020-01-01 00:00:00","proposition_dischtime":"2020-01-03 12:00:00",
                       "admissions_admittime":"2020-01-01 00:00:00","admissions_dischtime":"2020-01-02 12:00:00"} for a in ("human","llm")]
        evidence_a="Hospital Admission Start: 2020-01-01 00:00:00\nHospital Admission End: 2020-01-03 12:00:00\nevidence A"
        evidence_b="Hospital Admission Start: 2020-01-01 00:00:00\nHospital Admission End: 2020-01-02 12:00:00\nevidence B 中文"
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/"verifact").mkdir()
            db=duckdb.connect()
            db.execute("CREATE TABLE v (model VARCHAR,proposition_id VARCHAR,rater_alias VARCHAR,verdict VARCHAR,reason VARCHAR,reasoning_chain VARCHAR,reasoning_final_answer VARCHAR,reference_id VARCHAR)")
            db.executemany("INSERT INTO v VALUES (?,?,?,?,?,?,?,?)",[
                ("R1-70B","llm","R1-70B","Supported","explanation","reasoning","answer",digest_text(evidence_a)),
                ("Gemma-3-12B","llm","Gemma-3-12B","Supported","explanation",None,None,digest_text(evidence_b)),
                ("Gemma-3-12B","human","Gemma-3-12B","Supported","",None,None,digest_text(evidence_a)),
            ])
            db.table("v").write_parquet(str(base/"verifact/verdicts.parquet"))
            db.execute("CREATE TABLE ref (reference_id VARCHAR,reference VARCHAR)")
            db.executemany("INSERT INTO ref VALUES (?,?)",[(digest_text(t),t) for t in (evidence_a,evidence_b)])
            db.table("ref").write_parquet(str(base/"verifact/reference_payloads.parquet"))
            db.close()
            checks=Checks()
            summary,exports,_=audit_ai(base,{"rater_configurations":raters,"experiment_matrix":matrix,"model_metadata":models},propositions,checks,lambda _:None)
            self.assertFalse(checks.failed)
            self.assertEqual((summary["expected_verdict_rows"],summary["verdict_rows"],summary["missing_verdict_rows"]),(4,3,1))
            self.assertEqual(exports["missing_verdict_keys"][0]["proposition_id"],"human")
            self.assertEqual(summary["context_groups_with_different_payloads"],1)
            self.assertEqual(summary["empty_reasons"],1)
            self.assertEqual(summary["reference_header_mismatch_patients"],["1"])
            self.assertEqual(sum(r["matches_admissions"] for r in summary["reference_header_comparisons"]),1)
            self.assertEqual(sum(r["matches_propositions"] for r in summary["reference_header_comparisons"]),1)
            self.assertEqual(next(r["status"] for r in checks.rows if r["id"]=="references.content_sha256"),"pass")


if __name__ == "__main__":
    unittest.main()
