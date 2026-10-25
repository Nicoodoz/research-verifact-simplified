"""Independent, network-disabled audit of the submitted 005 materials.

All generated artifacts are isolated; no project experiment files are changed.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path("D:/Research-VeriFact")
TMP = Path("C:/Users/13359/AppData/Local/Temp/verifact_005_audit_ecimh4ls")
SOURCE = ROOT / "outputs/004_event_alignment_pilot/run_003"
TASK = ROOT / "tasks/005_pilot_effect_analysis"
RUN = ROOT / "outputs/005_pilot_effect_analysis/run_002"
FORMAL = RUN / "review_002"
ARMS = ("structured", "event_alignment")
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
textsha = lambda s: hashlib.sha256(s.encode("utf-8")).hexdigest()


def csvrows(path):
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def kind(gt, s, e):
    if s == e:
        return "both_correct" if gt == s else "both_wrong"
    if gt == e:
        return "improved"
    if gt == s:
        return "degraded"
    return "wrong_changed"


result = {"started_utc": datetime.now(timezone.utc).isoformat(), "base_head": "c4ff859b6e1ed991c3ce82ebaa7031c2729f9683",
          "version": read(TMP / "version_snapshot.json"), "new_inference_calls": 0}
assert not result["version"]["mismatches"]
protected_names = {str(p.relative_to(ROOT)).replace("\\", "/") for parent in (
    ROOT / "data/00_raw", ROOT / "outputs/004_event_alignment_pilot", ROOT / "reviews")
    for p in parent.rglob("*") if p.is_file() and p.suffix != ".pyc"}
protected_names |= {"outputs/003_error_analysis/patient_groups.json", ".gitignore", "environment.yml"}
pool_meta = read(ROOT / "outputs/service_tools/siliconflow_pool/verification_001/verification.json")
pool_names = {n for n in pool_meta["code_and_docs_sha256"] if n != "README.md"}
protected_names |= pool_names
before = {n:sha(ROOT / n) for n in sorted(protected_names)}
write(TMP / "protected_before.json", before)
attempts = []


def deny(*args, **kwargs):
    attempts.append(True)
    raise AssertionError("Independent audit forbids network")


with ExitStack() as guard:
    for target in ("socket.socket.connect", "socket.socket.connect_ex", "socket.create_connection"):
        guard.enter_context(patch(target, side_effect=deny))
    sys.path.insert(0, str(TASK))
    sys.path.insert(0, str(ROOT / "src"))
    with (TMP / "tests.log").open("x", encoding="utf-8", newline="\n") as log:
        with redirect_stdout(log), redirect_stderr(log):
            suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
            tested = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    assert tested.wasSuccessful()
    result["software_tests"] = {"run":tested.testsRun, "failures":len(tested.failures), "errors":len(tested.errors)}
    print("Independent software tests passed:", tested.testsRun, flush=True)

    import effect_analysis as effects
    import build_effect_review as builder
    import analyze_live
    config, cohort, terminal, receipts, checks, receipt_hashes = analyze_live.collect(SOURCE)
    inputs = {r["proposition_id"]:r for r in effects.pilot.jsonl(SOURCE / "inputs.jsonl")}
    responses = {(r["proposition_id"], r["arm"]):r for r in terminal if r["arm"] in ARMS}
    rows = csvrows(RUN / "all_transitions.csv")
    selected = csvrows(RUN / "selected_cases.csv")
    by_id = {r["proposition_id"]:r for r in rows}
    assert len(rows) == len(by_id) == len(cohort) == 421
    assert set(by_id) == {r["proposition_id"] for r in cohort}
    groups = read(ROOT / "outputs/003_error_analysis/patient_groups.json")["groups"]
    patients = {r["subject_id"] for r in cohort}
    assert len(patients) == 6 and patients <= set(groups["development"])
    assert not patients & set(groups["reserved_test"])
    seed = read(RUN / "manifest.json")["selection_seed"]
    assert seed == "005_pilot_effect_analysis/case-selection/v1:"
    for r in cohort:
        saved = by_id[r["proposition_id"]]
        assert all(saved[k] == str(v) for k,v in r.items())
        s, e = (responses[(r["proposition_id"], a)] for a in ARMS)
        assert s["status"] == e["status"] == "success"
        assert saved["structured"] == s["verdict"] and saved["event_alignment"] == e["verdict"]
        assert saved["outcome"] == kind(r["human_gt"], s["verdict"], e["verdict"])
        assert saved["selection_hash"] == textsha(seed + r["proposition_id"])
        assert saved["reference_id"] == inputs[r["proposition_id"]]["reference_id"]
        for a in ARMS:
            assert saved[a + "_strict_format"] == str(not responses[(r["proposition_id"],a)]["adherence_errors"])
    raw = ROOT / "data/00_raw/verifact-bhc/1.1.0/propositions"
    gt_rows = {}
    with gzip.open(raw / "human_verdicts.csv.gz", "rt", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["proposition_id"] in by_id:
                gt_rows[row["proposition_id"]] = row
    assert len(gt_rows) == 421
    for pid, r in by_id.items():
        doc = gt_rows[pid]
        assert r["human_gt"] == doc["human_gt"]
        count = max(Counter(doc["verdict"+str(i)] for i in (1,2,3)).values())
        assert int(r["initial_agreement"]) == (count if count >= 2 else 0)

    totals = {a:dict(Counter(r["outcome"] for r in rows if r["author_type"] == a)) for a in ("llm","human")}
    summary = {"correctness_changes":sum(r["outcome"] in ("improved","degraded") for r in rows),
        "supported_correctness_changes":sum(r["outcome"] in ("improved","degraded") and r["human_gt"] == "Supported" for r in rows),
        "supported_improvements":sum(r["outcome"] == "improved" and r["structured"] == "Not Supported" and r["event_alignment"] == "Supported" for r in rows),
        "supported_degradations":sum(r["outcome"] == "degraded" and r["structured"] == "Supported" and r["event_alignment"] == "Not Supported" for r in rows),
        "human_degraded_initial_three_agree":sum(r["author_type"] == "human" and r["outcome"] == "degraded" and r["initial_agreement"] == "3" for r in rows)}
    assert summary == read(ROOT / "outputs/005_pilot_effect_analysis/verification_001/final_checks.json")["report_counts_verified"]
    result["independent_counts"] = {"by_author":totals, "report_counts":summary}
    for name, fields in (("transition_counts",["author_type","outcome","human_gt",*ARMS]),
                         ("patient_counts",["subject_id","author_type","outcome"]),
                         ("annotation_counts",["author_type","initial_agreement","outcome"]),
                         ("adherence_counts",["author_type","structured_strict_format","event_alignment_strict_format","outcome"])):
        expected = Counter(tuple(r[k] for k in fields) for r in rows)
        got = {tuple(r[k] for k in fields):int(r["n"]) for r in csvrows(RUN / (name+".csv"))}
        assert expected == got, name

    # Derive the documented selection order without calling the submitted selector.
    chosen, global_counts = [], Counter()
    def add(r):
        chosen.append(r)
        global_counts[r["subject_id"]] += 1
    for a in ("llm","human"):
        for k in ("improved","degraded"):
            remaining = [r for r in rows if r["author_type"] == a and r["outcome"] == k]
            cells, own_counts = set(), Counter()
            for i in range(min(4,len(remaining))):
                order = lambda r: ((r["human_gt"],r["structured"],r["event_alignment"]) in cells,
                                    own_counts[r["subject_id"]], textsha(seed+r["proposition_id"]))
                r = sorted(remaining,key=order)[0]
                add(r); remaining.remove(r)
                cells.add((r["human_gt"],r["structured"],r["event_alignment"]))
                own_counts[r["subject_id"]] += 1
    for r in sorted([r for r in rows if r["outcome"] == "wrong_changed"],key=lambda r:textsha(seed+r["proposition_id"])):
        add(r)
    for a in ("llm","human"):
        for k, positive in (("both_correct",True),("both_correct",False),("both_wrong",True)):
            candidates = [r for r in rows if r["author_type"]==a and r["outcome"]==k and (r["human_gt"]=="Supported")==positive]
            add(sorted(candidates,key=lambda r:(global_counts[r["subject_id"]],textsha(seed+r["proposition_id"])))[0])
    assert [r["proposition_id"] for r in chosen] == [r["proposition_id"] for r in selected]
    assert [r["case_id"] for r in selected] == [f"C{i:02d}" for i in range(1,26)]
    assert sha(RUN / "selected_cases.csv") == sha(ROOT / "outputs/005_pilot_effect_analysis/run_001/selected_cases.csv")
    result["selection"] = {"cases":25,"independently_reproduced":True,"initial_partial_run_same":True,
        "outcomes":dict(Counter(r["outcome"] for r in selected))}

    packets = {p.stem:read(p) for p in (RUN / "packets").glob("*.json")}
    assert len(packets) == 64
    expected_ids = {r["proposition_id"] for r in rows if r["structured"] != r["event_alignment"]} | {r["proposition_id"] for r in selected}
    assert {p["input"]["proposition_id"] for p in packets.values()} == expected_ids
    for cid,p in packets.items():
        pid = p["input"]["proposition_id"]
        assert p["input"] == inputs[pid]
        for a in ARMS:
            assert p["outputs"][a] == responses[(pid,a)]
        assert p["selected_for_deep_review"] == cid.startswith("C")
    anchors = read(FORMAL / "evidence_anchors.json")
    anchor_types = Counter()
    for item in anchors:
        p = packets[item["case_id"]]
        assert item["proposition_id"] == p["input"]["proposition_id"]
        anchor_types[item["source"]] += 1
        if item["source"] == "reference":
            reference = p["input"]["reference"]
            assert item["reference_id"] == p["input"]["reference_id"] and textsha(reference) == item["source_sha256"]
            assert reference[item["start"]:item["end_exclusive"]] == item["quote"]
            assert reference[item["start"]-len(str(item["number"]))-2:item["start"]] == str(item["number"])+". "
        else:
            assert item["source"] == "model_output"
            raw_output = p["outputs"][item["arm"]]["output_text"]
            assert textsha(raw_output) == item["source_sha256"]
            idx = int(re.fullmatch(r"checks\[(\d+)\]",item["json_path"]).group(1))
            assert json.loads(raw_output)["checks"][idx] == item["check"]
    assert len(anchors) == 265
    result["anchors"] = {"count":len(anchors),"types":dict(anchor_types),"independent_identity_offsets_and_hashes":True}

    reconstructed, unique = defaultdict(dict), 0
    for file in (RUN / "reference_unions").glob("*.json"):
        for block in read(file):
            assert textsha(block["text"]) == block["block_id"]
            unique += 1
            for oc in block["occurrences"]:
                assert packets[oc["case"]]["input"]["subject_id"] == file.stem
                assert oc["number"] not in reconstructed[oc["case"]]
                reconstructed[oc["case"]][oc["number"]] = block["text"]
    for cid, actual in reconstructed.items():
        ref = packets[cid]["input"]["reference"]
        chunks = re.split(r"(?m)^(\d+)\. (?=Date: )",ref)
        expected = {int(chunks[i]):chunks[i+1].rstrip() for i in range(1,len(chunks),2)}
        assert expected == actual
    result["reference_union"] = {"unique_blocks":unique,"case_items":sum(map(len,reconstructed.values())),"full_text_items_preserved":True}
    contexts = read(RUN / "source_context.json")
    assert sha(ROOT / contexts["source"]) == contexts["source_sha256"]
    wanted = {r["proposition_id"]:r for r in contexts["cases"]}
    matched = {}
    with gzip.open(ROOT / contexts["source"],"rt",encoding="utf-8",newline="") as f:
        for r in csv.DictReader(f):
            if r["proposition_id"] in wanted:
                own = wanted[r["proposition_id"]]
                assert all(own[k] == r[k] for k in ("parent_text_chunk","brief_hospital_course"))
                assert r["text"] == packets[own["case_id"]]["input"]["text"]
                assert r["parent_text_chunk"] in r["brief_hospital_course"]
                matched[own["case_id"]] = True
    assert len(matched) == 13
    result["source_contexts_independently_matched"] = sorted(matched)

    with patch.object(effects,"OUT",TMP / "reextract"), redirect_stdout(io.StringIO()):
        effects.extract()
    rebuilt = TMP / "reextract/run_001"
    original_manifest = read(RUN / "manifest.json")
    identical = {n:sha(RUN/n)==sha(rebuilt/n) for n in original_manifest["outputs_sha256"]}
    assert len(identical) == 86 and all(identical.values())
    shutil.copy2(RUN / "source_context.json", rebuilt / "source_context.json")
    with redirect_stdout(io.StringIO()):
        rebuilt_review = builder.build(rebuilt,TASK/"review_notes.json",TASK/"report_template.md")
    report_manifest = read(FORMAL / "manifest.json")
    rendered = {n:sha(FORMAL/n)==sha(rebuilt_review/n) for n in report_manifest["outputs_sha256"]}
    assert len(rendered) == 30 and all(rendered.values())
    result["repeated_extraction_files"] = identical
    result["repeated_render_files"] = rendered
    result["metrics"] = {a:read(rebuilt/"metrics.json")[a]["contrast"]["metrics"] for a in ("llm","human")}
    result["shared_metrics_recomputed_and_equal_to_004"] = True
    print("Independent statistics, selection, 265 anchors, 86 extraction and 30 rendering files verified",flush=True)

    # Direct, isolated negative check of the public rendering entry point.
    altered = rebuilt / "packets/C17.json"
    old = altered.read_bytes()
    altered.write_bytes(old+b"\n")
    try:
        with redirect_stdout(io.StringIO()):
            builder.build(rebuilt,TASK/"review_notes.json",TASK/"report_template.md")
    except ValueError as exc:
        assert "Extraction artifact changed" in str(exc)
        result["altered_packet_rejected"] = True
    else:
        raise AssertionError("Changed packet accepted")
    finally:
        altered.write_bytes(old)

    result["scope"] = {"patients":len(patients),"claims":len(rows),"development_only":True,"reserved_case_access":False,
                       "account_pool_reviewed":False,"doctor_labels_modified":False}
    result["protected_file_count"] = len(before)
    result["protected_mismatches_after"] = [n for n,d in before.items() if sha(ROOT/n)!=d]
    result["submission_mismatches_after"] = [n for n,d in result["version"]["files_sha256"].items() if sha(ROOT/n)!=d]
    result["network_attempts"] = len(attempts)
    assert not result["protected_mismatches_after"] and not result["submission_mismatches_after"] and not attempts
    result["finished_utc"] = datetime.now(timezone.utc).isoformat()
    result["status"] = "mechanical_checks_passed; interpretation_audit_recorded_separately"
    write(TMP / "evidence.json",result)
    print(json.dumps({"status":result["status"],"counts":summary,"software_tests":tested.testsRun,
        "protected_files_unchanged":len(before),"evidence":str(TMP/"evidence.json")},ensure_ascii=False),flush=True)
