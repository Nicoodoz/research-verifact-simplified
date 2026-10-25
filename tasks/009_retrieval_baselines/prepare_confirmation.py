"""All valid claims for six fixed next development patients; local raw EHR corpus."""
from collections import Counter,defaultdict
import study009 as s
from prepare_experiment import embedding_jobs


def prepare():
    protocol=s.read_json(s.OUT/"confirmation_protocol_001.json")
    ids=protocol["patient_ids"]
    assert ids==s.patient_order()[18:24]
    assert protocol["main_methods"]==["A48","B48","C48"] and protocol["candidate_capacity"]==48
    master=s.ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    assert s.pilot.digest_file(master)==s.read_json(master.parent/"manifest.json")["output_sha256"]["cohort_master.csv"]
    all_rows=s.pilot.subset_csv(master,"subject_id",set(ids))
    cohort=[r for r in all_rows if r["proposition_type"]=="claim" and r["invalid"]=="False"]
    cohort.sort(key=lambda r:int(r["human_csv_order"]))
    assert len(cohort)==650 and len({r["proposition_id"] for r in cohort})==650
    props={p["proposition_id"]:p for p in s.pilot.subset_csv(s.RAW/"propositions/propositions.csv.gz","subject_id",set(ids))}
    admissions=s.pilot.subset_csv(s.RAW/"reference_ehr/admissions.csv.gz","SUBJECT_ID",set(ids))
    assert len(admissions)==len(ids)
    admissions={s.pilot.integer_id(a["SUBJECT_ID"]):a for a in admissions}
    notes=s.pilot.subset_csv(s.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",set(ids))
    inputs=[]
    for i,row in enumerate(cohort,1):
        prop=props[row["proposition_id"]]
        assert s.pilot.integer_id(prop["subject_id"])==row["subject_id"] and s.pilot.integer_id(prop["hadm_id"])==row["hadm_id"]
        inputs.append(dict(case_id=f"N{i:03d}",proposition_id=row["proposition_id"],subject_id=row["subject_id"],author_type=row["author_type"],
            text=prop["text"],admission=admissions[row["subject_id"]],claim_embedding_id=s.pilot.digest_text(prop["text"])))
    corpus,excluded=[],[]
    coverage=defaultdict(set)
    for note in sorted(notes,key=lambda n:int(n["ROW_ID"])):
        sid=s.pilot.integer_id(note["SUBJECT_ID"])
        a=admissions[sid]
        date=note["CHARTDATE"][:10]
        reason="missing_chartdate" if not date else "outside_admission_dates" if not a["ADMITTIME"][:10]<=date<=a["DISCHTIME"][:10] else "discharge_summary" if note["CATEGORY"].strip().lower()=="discharge summary" else None
        if reason:
            excluded.append(dict(subject_id=sid,note_id=note["ROW_ID"],date=date,reason=reason))
            continue
        for lo,hi in s.core.paragraph_spans(note["TEXT"]):
            p=dict(subject_id=sid,note_id=note["ROW_ID"],hadm_id=note["HADM_ID"],date=date,time=note["CHARTTIME"][11:] or "Unknown",
                category=note["CATEGORY"],description=note["DESCRIPTION"],start=lo,end_exclusive=hi,text=note["TEXT"][lo:hi],note_sha256=s.pilot.digest_text(note["TEXT"]))
            p["passage_id"]=s.pilot.fingerprint(p)
            p["search_text"]=f"Date: {p['date']}. {p['category']} {p['description']}. {p['text']}"
            p["embedding_id"]=s.pilot.digest_text(p["search_text"])
            corpus.append(p)
            coverage[note["ROW_ID"]].update(range(lo,hi))
        assert all(i in coverage[note["ROW_ID"]] for i,ch in enumerate(note["TEXT"]) if not ch.isspace()),"Incomplete raw coverage"
    corpus.sort(key=lambda p:p["passage_id"])
    catalog={p["embedding_id"]:p["search_text"] for p in corpus}
    catalog.update({x["claim_embedding_id"]:x["text"] for x in inputs})
    assert all(0<len(text.encode("utf-8"))<8192 for text in catalog.values())
    jobs=embedding_jobs(catalog,"009_confirm")
    out=s.OUT/"confirmation_001/preparation"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_csv(out/"cohort.csv",cohort)
    s.pilot.write_csv(out/"invalid_claims.csv",[r for r in all_rows if r["proposition_type"]=="claim" and r["invalid"]!="False"],fields=list(cohort[0]))
    s.pilot.write_csv(out/"excluded_notes.csv",excluded,fields=["subject_id","note_id","date","reason"])
    s.pilot.write_jsonl(out/"inputs.jsonl",inputs)
    s.pilot.write_jsonl(out/"corpus.jsonl",corpus)
    s.pilot.write_json(out/"embedding_catalog.json",catalog)
    s.pilot.write_jsonl(out/"jobs.jsonl",jobs)
    s.pilot.write_json(out/"judge_prompts.json",s.read_json(s.PRIOR/"preparation_001/judge_prompts.json"))
    summary=dict(patient_ids=ids,claims=len(cohort),all_valid_claims_included=True,by_author={a:dict(Counter(r["human_gt"] for r in cohort if r["author_type"]==a)) for a in ("llm","human")},
        indexed_notes=len(coverage),passages=len(corpus),embedding_texts=len(catalog),embedding_requests=len(jobs),
        indexed_date_extents={sid:[min(p["date"] for p in corpus if p["subject_id"]==sid),max(p["date"] for p in corpus if p["subject_id"]==sid)] for sid in ids},
        paragraphs_nonwhite_coverage_checked=True,old_numeric_embeddings_not_mixed=True,
        excluded_note_reasons=dict(Counter(x["reason"] for x in excluded)),clinical_data_source="Local raw EHR; no released reference used as retrieval result")
    s.pilot.write_json(out/"summary.json",summary)
    deps=[master,s.OUT/"confirmation_protocol_001.json",s.ROOT/"outputs/003_error_analysis/patient_groups.json"]
    deps += [s.RAW/name for name in ("propositions/propositions.csv.gz","reference_ehr/ehr_noteevents.csv.gz","reference_ehr/admissions.csv.gz")]
    s.seal(out,deps,[s.TASK/"prepare_confirmation.py",s.TASK/"study009.py",s.ROOT/"tasks/008_retrieval_planning/prepare_experiment.py"])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    prepare()
