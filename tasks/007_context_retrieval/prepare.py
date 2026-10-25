"""Prepare fixed cohorts, EHR passages and four queries; contains no paid API code."""
from collections import Counter
from datetime import datetime, timezone
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / "outputs/007_context_retrieval"
RAW = ROOT / "data/00_raw/verifact-bhc/1.1.0"
sys.path.insert(0,str(ROOT/"tasks/004_event_alignment_pilot"))
import pilot
import siliconflow as sf
from retrieval import ARMS, BM25, reference, retrieve, sentence_query, spans

SEED = "007_context_retrieval/selection/v1:"


def choose(rows, patients):
    selected = []
    for sid in patients:
        for author in ("llm", "human"):
            part = sorted((r for r in rows if r["subject_id"]==sid and r["author_type"]==author),key=lambda r:pilot.digest_text(SEED+r["proposition_id"]))
            chosen = [r for label in ("Not Supported","Not Addressed") for r in [x for x in part if x["human_gt"]==label][:3]]
            chosen += [r for r in part if r["human_gt"]=="Supported"][:12-len(chosen)]
            ids = {r["proposition_id"] for r in chosen}
            chosen += [r for r in part if r["proposition_id"] not in ids][:12-len(chosen)]
            selected += chosen
    return sorted(selected,key=lambda r:int(r["human_csv_order"]))


def corpus_for(patients, admissions, notes):
    corpora, exclusion = {}, []
    for sid in patients:
        admission = admissions[sid]
        start, end = admission["ADMITTIME"][:10], admission["DISCHTIME"][:10]
        passages = []
        for row in notes:
            if pilot.integer_id(row["SUBJECT_ID"]) != sid:
                continue
            reason = "outside_admission_calendar_dates" if not start <= row["CHARTDATE"][:10] <= end else "discharge_summary_excluded" if row["CATEGORY"].strip().lower()=="discharge summary" else None
            if reason:
                exclusion.append(dict(subject_id=sid,note_id=row["ROW_ID"],reason=reason))
                continue
            for lo, hi in spans(row["TEXT"]):
                text = row["TEXT"][lo:hi]
                p = dict(subject_id=sid,note_id=row["ROW_ID"],hadm_id=row["HADM_ID"],
                    date=row["CHARTDATE"][:10],time=row["CHARTTIME"][11:] or "Unknown",category=row["CATEGORY"],
                    description=row["DESCRIPTION"],start=lo,end_exclusive=hi,text=text,note_sha256=pilot.digest_text(row["TEXT"]))
                p["passage_id"] = pilot.fingerprint(p)
                p["search_text"] = p["date"]+" "+p["category"]+" "+p["description"]+" "+text
                passages.append(p)
        corpora[sid] = sorted(passages,key=lambda r:r["passage_id"])
        pilot.require(passages,"No patient EHR corpus")
    return corpora, exclusion


def run():
    OUT.mkdir(parents=True,exist_ok=True)
    output = OUT / "preparation_003"
    pilot.require(not output.exists(),"Preparation already exists")
    split_path = ROOT / "outputs/003_error_analysis/patient_groups.json"
    split = json.loads(split_path.read_text(encoding="utf-8"))
    order = sorted(split["groups"]["development"],key=lambda sid:pilot.digest_text(split["seed"]+sid))
    patients = order[8:12]
    pilot.require(patients==["21706","55204","65399","47874"],"Unexpected development order")
    master = ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    master_rows = pilot.subset_csv(master,"subject_id",set(patients))
    universe = [r for r in master_rows if r["proposition_type"]=="claim" and r["invalid"]=="False"]
    cohort = choose(universe,patients)
    # Old cases are used only for offline hypothesis probes, never mixed into new metrics.
    old = []
    for cid in ("N15","N23","N25","N45","N50","N56"):
        p = json.loads((ROOT/"outputs/006_source_context_feasibility/run_001/review_001/packets"/(cid+".json")).read_text(encoding="utf-8"))
        old.append(dict(p["case"],case_id="006_"+cid))
    for cid in ("C17","C18"):
        p = json.loads((ROOT/"outputs/005_pilot_effect_analysis/run_002/packets"/(cid+".json")).read_text(encoding="utf-8"))
        old.append(dict(p["cohort"],case_id="005_"+cid))
    ids = {r["proposition_id"] for r in cohort+old}
    all_patients = set(patients) | {r["subject_id"] for r in old}
    props_rows = pilot.subset_csv(RAW/"propositions/propositions.csv.gz","subject_id",all_patients)
    props = {r["proposition_id"]:r for r in props_rows if r["proposition_id"] in ids}
    notes = pilot.subset_csv(RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",all_patients)
    admissions = {pilot.integer_id(r["SUBJECT_ID"]):r for r in pilot.subset_csv(RAW/"reference_ehr/admissions.csv.gz","SUBJECT_ID",all_patients)}
    pilot.require(len(admissions)==len(all_patients),"Admission coverage mismatch")
    corpora, exclusions = corpus_for(all_patients,admissions,notes)
    indexes = {sid:BM25(c) for sid,c in corpora.items()}
    inputs, old_results = [], []
    for position, row in enumerate(cohort+old):
        prop = props[row["proposition_id"]]
        parent, bhc = prop["parent_text_chunk"], prop["brief_hospital_course"]
        pilot.require(parent and bhc.count(parent)==1,"Ambiguous parent origin")
        sid = row["subject_id"]
        sent, rule = sentence_query(prop["text"],parent,[s for s in props_rows if s["subject_id"].removesuffix(".0")==sid and s["author_type"]==row["author_type"] and s["proposition_type"]=="sentence"])
        parent_start = bhc.index(parent)
        local_start = max(0,parent_start-240)
        local_end = parent_start+len(parent)
        queries = dict(claim=prop["text"],sentence=sent,local=bhc[local_start:local_end])
        results = retrieve(indexes[sid],queries)
        for arm in ARMS:
            results[arm]["reference"] = reference(results[arm],admissions[sid])
            results[arm]["reference_id"] = pilot.digest_text(results[arm]["reference"])
        item = dict(case_id=f"R{position+1:03d}" if position<len(cohort) else row["case_id"],
            proposition_id=row["proposition_id"],subject_id=sid,author_type=row["author_type"],text=prop["text"],
            queries=queries,sentence_selection=rule,parent_text=parent,parent_start=parent_start,
            local_start=local_start,local_end_exclusive=local_end,bhc_sha256=pilot.digest_text(bhc),
            admission=admissions[sid],time_metadata_conflict=row.get("time_metadata_conflict"),retrieval=results)
        (inputs if position<len(cohort) else old_results).append(item)
    prompts = {n:(ROOT/"tasks/004_event_alignment_pilot/prompts"/(n+".md")).read_text(encoding="utf-8") for n in ("common","structured")}
    system = prompts["common"]+"\n"+prompts["structured"]
    jobs = []
    permutations = list(itertools.permutations(ARMS))
    ordered = sorted(inputs,key=lambda r:pilot.digest_text("007/order/v1:"+r["proposition_id"]))
    repeats = {min([r for r in inputs if r["subject_id"]==sid and r["author_type"]==author],key=lambda r:pilot.digest_text("007/repeat/v1:"+r["proposition_id"]))["proposition_id"] for sid in patients for author in ("llm","human") if any(r["subject_id"]==sid and r["author_type"]==author for r in inputs)}
    for i,item in enumerate(ordered):
        for arm in permutations[i%24]:
            body = dict(model=sf.MODEL,messages=[dict(role="system",content=system),dict(role="user",content=pilot.canonical(dict(proposition=item["text"],reference=item["retrieval"][arm]["reference"])))],
                temperature=0,max_tokens=2048,enable_thinking=False,n=1,stream=False,response_format=sf.response_schema())
            bound = ((len(pilot.canonical(body).encode("utf-8"))+1000)*3+2048*9)/1e6
            jobs.append(dict(request_id=arm+":"+item["proposition_id"],body=body,max_cost_cny=bound))
            if arm=="claim" and item["proposition_id"] in repeats:
                jobs.append(dict(request_id="claim_repeat:"+item["proposition_id"],body=body,max_cost_cny=bound))
    output.mkdir()
    pilot.write_csv(output/"cohort.csv",cohort)
    pilot.write_csv(output/"candidate_universe.csv",universe)
    pilot.write_csv(output/"not_selected.csv",[r for r in universe if r["proposition_id"] not in ids])
    pilot.write_csv(output/"excluded_notes.csv",exclusions,fields=["subject_id","note_id","reason"])
    pilot.write_json(output/"corpora.json",corpora)
    pilot.write_jsonl(output/"inputs.jsonl",inputs)
    pilot.write_jsonl(output/"old_case_probes.jsonl",old_results)
    pilot.write_jsonl(output/"requests.jsonl",jobs)
    pilot.write_json(output/"prompts.json",prompts)
    summary = dict(patients=patients,old_probe_patients=sorted(all_patients-set(patients)),
        candidate_claims=len(universe),selected_claims=len(cohort),requests=len(jobs),repeat_requests=len(repeats),
        by_author={a:dict(Counter(r["human_gt"] for r in cohort if r["author_type"]==a)) for a in ("llm","human")},
        corpus_passages={sid:len(c) for sid,c in corpora.items()},
        query_sentence_rule_counts=dict(Counter(r["sentence_selection"] for r in inputs)),
        mean_reference_chars={a:sum(len(r["retrieval"][a]["reference"]) for r in inputs)/len(inputs) for a in ARMS},
        identical_reference_to_claim={a:sum(r["retrieval"][a]["reference_id"]==r["retrieval"]["claim"]["reference_id"] for r in inputs) for a in ARMS},
        expected_no_cache_peak_cny=sum((sum(len(m["content"]) for m in j["body"]["messages"])*.4*3+450*9)/1e6 for j in jobs),
        conservative_all_attempt_byte_reservation_cny=sum(j["max_cost_cny"] for j in jobs),cap_cny=16,
        exactly_equivalent_to_original_Verifact_retrieval=False,exact_tokenizer_available=False)
    pilot.write_json(output/"summary.json",summary)
    raw_names=["propositions/propositions.csv.gz","reference_ehr/ehr_noteevents.csv.gz","reference_ehr/admissions.csv.gz"]
    pilot.write_json(output/"manifest.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in [Path(__file__),TASK/"retrieval.py"]},
        raw_sha256={n:pilot.digest_file(RAW/n) for n in raw_names},cohort_master_sha256=pilot.digest_file(master),
        patient_split_sha256=pilot.digest_file(split_path),output_sha256={p.name:pilot.digest_file(p) for p in output.iterdir() if p.is_file()},
        stage="offline_prepared_before_model_results"))
    print(pilot.canonical(summary))


if __name__=="__main__":
    run()
