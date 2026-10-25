"""All-case index/ranking/packing diagnostics; no claim of medical recall or precision."""
from collections import defaultdict,Counter
from pathlib import Path
import argparse
import re
import study009 as s


def analyze(folder):
    prep=folder/"preparation"
    s.check(prep)
    s.check(folder/"judge_preparation")
    inputs=s.pilot.jsonl(folder/"judge_preparation/inputs.jsonl")
    corpus=s.pilot.jsonl(prep/"corpus.jsonl")
    pp={p["passage_id"]:p for p in corpus}
    subjects={x["subject_id"] for x in inputs}
    notes={n["ROW_ID"]:n for n in s.pilot.subset_csv(s.RAW/"reference_ehr/ehr_noteevents.csv.gz","SUBJECT_ID",subjects)}
    note_passages=defaultdict(list)
    equivalents=defaultdict(set)
    forced_neighbors=defaultdict(set)
    for p in corpus:
        raw=notes[p["note_id"]]
        assert p["text"]==raw["TEXT"][p["start"]:p["end_exclusive"]]
        assert p["note_sha256"]==s.pilot.digest_text(raw["TEXT"])
        assert p["subject_id"]==s.pilot.integer_id(raw["SUBJECT_ID"])
        note_passages[p["note_id"]].append(p)
        equivalents[(p["subject_id"],p["date"],p["category"],p["text"])].add(p["passage_id"])
    for nid,parts in note_passages.items():
        parts.sort(key=lambda p:p["start"])
        for left,right in zip(parts,parts[1:]):
            gap=notes[nid]["TEXT"][left["end_exclusive"]:right["start"]]
            if not re.search(r"\n[ \t\r]*\n",gap):
                forced_neighbors[left["passage_id"]].add(right["passage_id"])
                forced_neighbors[right["passage_id"]].add(left["passage_id"])
    def textkey(k):
        p=pp[k]
        return p["subject_id"],p["date"],p["category"],p["text"]
    rows=[]
    for item in inputs:
        ranks=item["rankings"]
        for method in ("A48","B48","C48"):
            r=item["retrieval"][method]
            if r["status"]!="ready":
                continue
            pool=set(r["candidate_ids"])
            selected=set(r["selected_ids"])
            textgroups={textkey(k) for k in selected}
            same_note_time_collisions=sum(len({pp[k]["time"] for k in equivalents[group]})>1 for group in textgroups)
            rows.append(dict(proposition_id=item["proposition_id"],case_id=item["case_id"],subject_id=item["subject_id"],method=method,
                candidate_count=len(pool),candidate_unique_literal=len({textkey(k) for k in pool}),selected_count=len(selected),
                dense_top24_excluded=len({k for k,_ in ranks.get("dense",[])[:24]}-pool),
                bm25_top24_excluded=len({k for k,_ in ranks.get("bm25",[])[:24]}-pool),
                selected_tiny=sum(len(pp[k]["text"].strip())<40 for k in selected),
                selected_single_line_heading=sum(len(pp[k]["text"].strip().splitlines())==1 and pp[k]["text"].rstrip().endswith(":") for k in selected),
                selected_no_letters=sum(not re.search(r"[A-Za-z]",pp[k]["text"]) for k in selected),
                selected_with_missing_length_split_neighbor=sum(bool(forced_neighbors[k]-selected) for k in selected),
                dedup_groups_with_different_record_times=same_note_time_collisions,
                first_binding_skip_reasons=dict(Counter(x["reason"] for x in r["selection_skips"])),
                branch_rerank_scores_all_real=set(r["candidate_ids"])<=set(item["scores"])))
    availability=[]
    for sid in sorted(subjects):
        item=next(x for x in inputs if x["subject_id"]==sid)
        admit=item["admission"]
        in_scope=[n for n in notes.values() if s.pilot.integer_id(n["SUBJECT_ID"])==sid and admit["ADMITTIME"][:10]<=n["CHARTDATE"][:10]<=admit["DISCHTIME"][:10] and n["CATEGORY"].strip().lower()!="discharge summary"]
        indexed={p["note_id"] for p in corpus if p["subject_id"]==sid}
        missing=[n["ROW_ID"] for n in in_scope if n["TEXT"].strip() and n["ROW_ID"] not in indexed]
        assert not missing,"Nonempty in-scope EHR note absent from index"
        availability.append(dict(subject_id=sid,admit=admit["ADMITTIME"],discharge=admit["DISCHTIME"],in_scope_notes=len(in_scope),indexed_notes=len(indexed),
            last_in_scope_record_date=max((n["CHARTDATE"][:10] for n in in_scope),default=None),missing_indexed_ids=missing,
            category_counts=dict(Counter(n["CATEGORY"] for n in in_scope))))
    summary=dict(claims=len(inputs),corpus_passages=len(corpus),raw_spans_verified=True,no_nonempty_in_scope_note_lost_at_index=True,
        all_ready_candidates_have_real_rerank_scores=all(r["branch_rerank_scores_all_real"] for r in rows),
        by_method={a:{key:sum(r[key] for r in rows if r["method"]==a) for key in ("candidate_count","candidate_unique_literal","selected_count","dense_top24_excluded","bm25_top24_excluded","selected_tiny","selected_single_line_heading","selected_no_letters","selected_with_missing_length_split_neighbor","dedup_groups_with_different_record_times")} for a in ("A48","B48","C48")},
        counts_are_occurrences_not_medical_gold=True,skip_reason_interpretation="First binding rule, not exclusive clinical causes; short or split does not imply irrelevant")
    out=folder/"loss_map_001"
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/"all_claim_diagnostics.jsonl",rows)
    s.pilot.write_json(out/"availability.json",availability)
    s.pilot.write_json(out/"summary.json",summary)
    s.seal(out,[prep/"manifest.json",folder/"judge_preparation/manifest.json",s.RAW/"reference_ehr/ehr_noteevents.csv.gz"],[Path(__file__)])
    print(s.pilot.canonical(summary))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path)
    analyze(p.parse_args().folder.resolve())
