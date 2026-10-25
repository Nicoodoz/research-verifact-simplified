"""Offline, fixed-patient preparation; no API calls."""
from collections import Counter
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import common as c
from planning_core import source_context,paragraph_spans


def choose(rows):
    chosen=[]
    for sid in c.PATIENTS:
        for author in ("llm","human"):
            part=sorted([r for r in rows if r["subject_id"]==sid and r["author_type"]==author],key=lambda r:c.pilot.digest_text("008/selection/v1:"+r["proposition_id"]))
            selected=[r for label in ("Not Supported","Not Addressed") for r in [x for x in part if x["human_gt"]==label][:3]]
            selected += [r for r in part if r["human_gt"]=="Supported"][:max(0,12-len(selected))]
            used={r["proposition_id"] for r in selected}
            selected += [r for r in part if r["proposition_id"] not in used][:max(0,12-len(selected))]
            chosen += selected
    return sorted(chosen,key=lambda r:int(r["human_csv_order"]))


def embedding_jobs(catalog,phase):
    entries=sorted(catalog.items())
    return [dict(request_id=f"{phase}_{i//16:04d}",kind="embedding",body=dict(model=c.EMBED_MODEL,
        input=[t for _,t in entries[i:i+16]],encoding_format="float"),text_ids=[key for key,_ in entries[i:i+16]]) for i in range(0,len(entries),16)]


def prepare():
    out=c.OUT/"preparation_001"
    out.mkdir(parents=True,exist_ok=False)
    split_path=c.ROOT/"outputs/003_error_analysis/patient_groups.json"
    split=c.read_json(split_path)
    order=sorted(split["groups"]["development"],key=lambda sid:c.pilot.digest_text(split["seed"]+sid))
    c.pilot.require(order[12:18]==c.PATIENTS,"Patient order changed")
    master=c.ROOT/"outputs/002_reproduce_paper_results/run_003/cohort_master.csv"
    c.pilot.require(c.pilot.digest_file(master)==c.read_json(master.parent/"manifest.json")["output_sha256"]["cohort_master.csv"],"Original cohort changed")
    allrows=c.pilot.subset_csv(master,"subject_id",set(c.PATIENTS))
    rows=[r for r in allrows if r["proposition_type"]=="claim" and r["invalid"]=="False"]
    cohort=choose(rows)
    props=c.pilot.subset_csv(c.RAW/"propositions/propositions.csv.gz","subject_id",set(c.PATIENTS))
    prop_lookup={r["proposition_id"]:r for r in props}
    admissions={c.pilot.integer_id(r["SUBJECT_ID"]):r for r in c.pilot.subset_csv(c.RAW/"reference_ehr/admissions.csv.gz","SUBJECT_ID",set(c.PATIENTS))}
    notes=c.pilot.subset_csv(c.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",set(c.PATIENTS))
    inputs=[]
    for i,row in enumerate(cohort,1):
        prop=prop_lookup[row["proposition_id"]]
        assert c.pilot.integer_id(prop["subject_id"])==row["subject_id"] and c.pilot.integer_id(prop["hadm_id"])==row["hadm_id"]
        sentences=[x for x in props if x["proposition_type"]=="sentence" and x["author_type"]==row["author_type"]]
        inputs.append(dict(case_id=f"P{i:03d}",proposition_id=row["proposition_id"],subject_id=row["subject_id"],author_type=row["author_type"],
            text=prop["text"],source=source_context(prop,sentences),admission=admissions[row["subject_id"]]))
    corpus,excluded=[],[]
    for note in sorted(notes,key=lambda x:int(x["ROW_ID"])):
        sid=c.pilot.integer_id(note["SUBJECT_ID"])
        admission=admissions[sid]
        reason="outside_admission_dates" if not admission["ADMITTIME"][:10]<=note["CHARTDATE"][:10]<=admission["DISCHTIME"][:10] else "discharge_summary" if note["CATEGORY"].strip().lower()=="discharge summary" else None
        if reason:
            excluded.append(dict(subject_id=sid,note_id=note["ROW_ID"],reason=reason))
            continue
        for lo,hi in paragraph_spans(note["TEXT"]):
            item=dict(subject_id=sid,note_id=note["ROW_ID"],hadm_id=note["HADM_ID"],date=note["CHARTDATE"][:10],time=note["CHARTTIME"][11:] or "Unknown",
                category=note["CATEGORY"],description=note["DESCRIPTION"],start=lo,end_exclusive=hi,text=note["TEXT"][lo:hi],note_sha256=c.pilot.digest_text(note["TEXT"]))
            item["passage_id"]=c.pilot.fingerprint(item)
            item["search_text"]=f"Date: {item['date']}. {item['category']} {item['description']}. {item['text']}"
            item["embedding_id"]=c.pilot.digest_text(item["search_text"])
            corpus.append(item)
    corpus.sort(key=lambda x:x["passage_id"])
    catalog={p["embedding_id"]:p["search_text"] for p in corpus}
    for x in inputs:
        for query in (x["text"],x["source"]["sentence"],x["source"]["local"]):
            catalog[c.pilot.digest_text(query)]=query
    c.pilot.require(all(0<len(x.encode("utf-8"))<8192 for x in catalog.values()),"Embedding input beyond conservative byte screen")
    planner_prompt=(c.TASK/"planner_prompt.md").read_text(encoding="utf-8")
    planners=[]
    for item in sorted(inputs,key=lambda x:c.pilot.digest_text("008/planner-order/v1:"+x["proposition_id"])):
        planners.append(dict(request_id="plan:"+item["proposition_id"],kind="chat",body=dict(model=c.CHAT_MODEL,
            messages=[dict(role="system",content=planner_prompt),dict(role="user",content=c.pilot.canonical(dict(claim=item["text"],source_context=item["source"]["local"])))],
            temperature=0,max_tokens=1500,enable_thinking=False,n=1,stream=False,response_format=dict(type="json_object"))))
    c.pilot.write_csv(out/"cohort.csv",cohort)
    c.pilot.write_csv(out/"candidate_universe.csv",rows)
    chosen={r["proposition_id"] for r in cohort}
    c.pilot.write_csv(out/"not_selected.csv",[r for r in rows if r["proposition_id"] not in chosen])
    c.pilot.write_csv(out/"excluded_notes.csv",excluded,fields=["subject_id","note_id","reason"])
    c.pilot.write_jsonl(out/"inputs.jsonl",inputs)
    c.pilot.write_jsonl(out/"corpus.jsonl",corpus)
    c.pilot.write_json(out/"embedding_catalog.json",catalog)
    c.pilot.write_jsonl(out/"planner_jobs.jsonl",planners)
    c.pilot.write_jsonl(out/"embedding_base_jobs.jsonl",embedding_jobs(catalog,"base"))
    c.pilot.write_json(out/"judge_prompts.json",{name:(c.ROOT/"tasks/004_event_alignment_pilot/prompts"/(name+".md")).read_text(encoding="utf-8") for name in ("common","structured")})
    estimate_planner=sum((sum(len(m["content"]) for m in j["body"]["messages"])*.4*3+600*9)/1e6 for j in planners)
    worst_judge_calls=len(inputs)*3+12
    estimate_judge=worst_judge_calls*(4000*3+450*9)/1e6
    estimate_embed=sum(len(t)*.4*.07/1e6 for t in catalog.values())+.01
    estimate_rerank=len(inputs)*144*250*.07/1e6
    summary=dict(patient_ids=c.PATIENTS,valid_candidate_claims=len(rows),selected_claims=len(cohort),by_author={a:dict(Counter(r["human_gt"] for r in cohort if r["author_type"]==a)) for a in ("llm","human")},
        by_patient={s:sum(r["subject_id"]==s for r in cohort) for s in c.PATIENTS},corpus_passages=len(corpus),included_notes=len({p["note_id"] for p in corpus}),
        max_source_chars=max(len(x["source"]["local"]) for x in inputs),embedding_texts=len(catalog),embedding_base_requests=len(embedding_jobs(catalog,"base")),
        planner_requests=len(planners),judge_requests_before_cache_ceiling=worst_judge_calls,phase_caps_cny=c.PHASE_CAPS,
        estimates_cny=dict(planner=estimate_planner,embeddings=estimate_embed,rerank=estimate_rerank,judge=estimate_judge),
        expected_total_cny=estimate_planner+estimate_embed+estimate_rerank+estimate_judge,task_cap_cny=40,api_calls=0,
        no_equivalence_to_original_Verifact_index_claim=True)
    c.pilot.write_json(out/"summary.json",summary)
    raw_names=["propositions/propositions.csv.gz","reference_ehr/ehr_noteevents.csv.gz","reference_ehr/admissions.csv.gz"]
    c.pilot.write_json(out/"manifest.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=c.ROOT,text=True).strip(),
        raw_sha256={n:c.pilot.digest_file(c.RAW/n) for n in raw_names},split_sha256=c.pilot.digest_file(split_path),cohort_master_sha256=c.pilot.digest_file(master),
        code_sha256={p.relative_to(c.ROOT).as_posix():c.pilot.digest_file(p) for p in [Path(__file__),c.TASK/"planning_core.py",c.TASK/"common.py",c.TASK/"planner_prompt.md"]},
        files={p.name:c.pilot.digest_file(p) for p in out.iterdir() if p.is_file()}))
    print(c.pilot.canonical(summary))


if __name__=="__main__":
    prepare()
