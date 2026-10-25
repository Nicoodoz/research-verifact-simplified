"""Audit propositions, clinician annotations, documents, admissions and EHR."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime

from .common import (LABELS, Checks, digest_text, distribution, integer_id,
                     literal_positions, majority)


def key_audit(rows: list[dict], field: str, table: str, checks: Checks) -> None:
    counts = Counter(r[field] for r in rows)
    bad = {key: n for key, n in counts.items() if not key or n > 1}
    checks.add(f"keys.{table}.{field}", not bad, bad, "non-empty unique key", table)


def audit_cohort(tables: dict, subject_ids: list[str], checks: Checks) -> tuple[dict, dict, list[dict]]:
    ps, hs, vs = (tables[name] for name in ("propositions", "human_verdicts", "proposition_validity"))
    notes, admissions = tables["ehr_noteevents"], tables["admissions"]
    admission_lookup = {integer_id(r["HADM_ID"]):r for r in admissions}
    for table, field in [("propositions", "proposition_id"), ("human_verdicts", "proposition_id"),
                         ("proposition_validity", "proposition_id"), ("ehr_noteevents", "ROW_ID"),
                         ("admissions", "HADM_ID"), ("model_metadata", "model"),
                         ("rater_configurations", "rater_alias")]:
        key_audit(tables[table], field, table, checks)
    h = {r["proposition_id"]: r for r in hs}
    v = {r["proposition_id"]: r for r in vs}
    pids = {r["proposition_id"] for r in ps}
    for name, other in [("human_verdicts", h), ("proposition_validity", v)]:
        checks.add(f"fk.{name}.propositions", set(other) == pids,
                   {"missing": sorted(pids-set(other)), "extra": sorted(set(other)-pids)},
                   "exactly the same proposition IDs", name)
        mismatches = [r["proposition_id"] for r in ps if r["proposition_id"] in other and
                      any(r[f] != other[r["proposition_id"]][f] for f in ("text", "author_type", "proposition_type"))]
        checks.add(f"alignment.{name}.metadata", not mismatches, mismatches, [], name)
    if not pids <= h.keys() or not pids <= v.keys():
        raise ValueError("Cannot construct paired cohort: required annotations missing")

    patients = {integer_id(r["subject_id"]) for r in ps}
    sets = {"subject_ids.txt": set(subject_ids), "admissions": {integer_id(r["SUBJECT_ID"]) for r in admissions},
            "ehr_noteevents": {integer_id(r["SUBJECT_ID"]) for r in notes}}
    for name, observed in sets.items():
        checks.add(f"patients.coverage.{name}", observed == patients,
                   {"missing": sorted(patients-observed), "extra": sorted(observed-patients)},
                   "same patients as propositions", name)
    checks.add("patients.subject_list_unique", len(subject_ids) == len(set(subject_ids)),
               len(subject_ids)-len(set(subject_ids)), 0, "subject_ids.txt")
    checks.add("domains.proposition_types", {r["proposition_type"] for r in ps} == {"claim", "sentence"},
               sorted({r["proposition_type"] for r in ps}), ["claim", "sentence"], "propositions")
    checks.add("domains.author_types", {r["author_type"] for r in ps} == {"human", "llm"},
               sorted({r["author_type"] for r in ps}), ["human", "llm"], "propositions")
    checks.add("domains.human_gt", all(r["human_gt"] in LABELS for r in hs),
               dict(Counter(r["human_gt"] for r in hs)), list(LABELS), "human_verdicts")
    flag_fields = [f for f in vs[0] if f not in {"proposition_id", "text", "author_type", "proposition_type"}]
    bad_bools = [{"id": r["proposition_id"], "field": f, "value": r[f]} for r in vs
                 for f in flag_fields if r[f] not in {"True", "False"}]
    checks.add("domains.validity_booleans", not bad_bools, bad_bools, [], "proposition_validity")

    exports: dict[str, list[dict]] = {}
    joined, annotation_errors, validity_errors, overlap = [], [], [], []
    round2_errors, sentence_chunk_errors = [], []
    groups, documents = defaultdict(list), defaultdict(list)
    agreement_counts, round2_counts = Counter(), Counter()
    annotators = set()
    for p in ps:
        pid = p["proposition_id"]
        g, flags = h[pid], v[pid]
        votes = [g[f"verdict{i}"] for i in (1, 2, 3)]
        try:
            count, vote = majority(votes)
        except ValueError:
            annotation_errors.append({"proposition_id": pid, "issue": "invalid first-round votes"})
            count, vote = -1, None
        agreement_counts[count] += 1
        round2_counts[g["round2_decision"]] += 1
        annotators.update(g[f"rater{i}"] for i in (1, 2, 3) if g[f"rater{i}"])
        expected_gt = vote if vote else g["adjudicated_verdict"]
        if str(count) != g["round1_num_raters_agree"] or (vote or "") != g["round1_majority_vote"] or expected_gt != g["human_gt"]:
            annotation_errors.append({"proposition_id": pid, "issue": "majority/agreement/final label mismatch"})
        if len({g[f"rater{i}"] for i in (1, 2, 3)}) != 3 or any(not g[f"rater{i}"] for i in (1, 2, 3)):
            annotation_errors.append({"proposition_id": pid, "issue": "missing or repeated initial rater"})
        if count == 0 and any(not g[f] for f in ("rater4", "rater5", "verdict4", "verdict5", "adjudicated_verdict")):
            annotation_errors.append({"proposition_id": pid, "issue": "all-different row lacks later-stage annotation"})
        if count == 0:
            later = [g['verdict4'], g['verdict5']]
            decision = 'Agree' if later[0] == later[1] else 'Disagree'
            if (any(label not in LABELS for label in later) or g['round2_decision'] != decision
                    or g['rater4'] == g['rater5']
                    or (decision == 'Agree' and g['adjudicated_verdict'] != later[0])):
                round2_errors.append({'proposition_id': pid, 'issue': 'second-round votes/decision/final verdict mismatch'})
        elif any(g[field] for field in ('rater4', 'rater5', 'verdict4', 'verdict5', 'round2_decision', 'adjudicated_verdict')):
            round2_errors.append({'proposition_id': pid, 'issue': 'later-stage fields populated on a first-round majority row'})
        invalid = flags["invalid"] == "True"
        if invalid != any(flags[f] == "True" for f in ("imperative", "interrogative", "incomplete", "vague")):
            validity_errors.append({"proposition_id": pid, "issue": "invalid != OR(final component flags)"})
        sid, hadm = integer_id(p["subject_id"]), integer_id(p["hadm_id"])
        doc_key = f"{sid}:{hadm}:{p['author_type']}"
        positions = literal_positions(p["brief_hospital_course"], p["text"])
        chunk_positions = literal_positions(p["brief_hospital_course"], p["parent_text_chunk"])
        if p['proposition_type'] == 'sentence' and not literal_positions(p['parent_text_chunk'], p['text']):
            sentence_chunk_errors.append(pid)
        row = {"proposition_id": pid, "subject_id": sid, "hadm_id": hadm,
               "proposition_admittime": p["admitdate"]+" "+p["admittime"],
               "proposition_dischtime": p["dischargedate"]+" "+p["dischargetime"],
               "admissions_admittime": admission_lookup.get(hadm,{}).get("ADMITTIME"),
               "admissions_dischtime": admission_lookup.get(hadm,{}).get("DISCHTIME"),
               "author_type": p["author_type"], "proposition_type": p["proposition_type"],
               "document_key": doc_key, "source_row_id": integer_id(p["row_id"]),
               "text_sha256": digest_text(p["text"]), "text_characters": len(p["text"]),
               "parent_chunk_sha256": digest_text(p["parent_text_chunk"]),
               "parent_chunk_characters": len(p["parent_text_chunk"]),
               "human_gt": g["human_gt"], "invalid": invalid, "initial_agreement": count,
               "literal_text_matches_in_bhc": len(positions),
               "literal_chunk_matches_in_bhc": len(chunk_positions),
               "unique_text_start": positions[0] if len(positions) == 1 else None,
               "unique_text_end_exclusive": positions[0] + len(p["text"]) if len(positions) == 1 else None,
               "initial_uncertain_votes": sum(g[f"uncertain_flag{i}"] == "True" for i in (1, 2, 3))}
        joined.append(row)
        groups[(p["author_type"], p["proposition_type"])].append((p, g, flags, row))
        documents[doc_key].append(p)
    checks.add("human.majority_and_adjudication", not annotation_errors, len(annotation_errors), 0, "annotation_anomalies.csv")
    checks.add('human.second_round_consistency', not round2_errors, len(round2_errors), 0, 'second_round_anomalies.csv; paper p4 annotation flow')
    annotation_errors.extend(round2_errors)
    p_lookup = {row['proposition_id']: row for row in ps}
    round2_details = []
    for error in round2_errors:
        pid = error['proposition_id']
        row = h[pid]
        round2_details.append({**error, 'subject_id': integer_id(p_lookup[pid]['subject_id']),
                               'hadm_id': integer_id(p_lookup[pid]['hadm_id']),
                               **{f: row[f] for f in ('author_type', 'proposition_type', 'rater4', 'rater5',
                                                      'verdict4', 'verdict5', 'round2_decision',
                                                      'adjudicated_verdict', 'human_gt')}})
    checks.add("validity.final_union", not validity_errors, len(validity_errors), 0, "validity_anomalies.csv")
    checks.add("source_chunks.literal_substring", all(r["literal_chunk_matches_in_bhc"] > 0 for r in joined),
               sum(r["literal_chunk_matches_in_bhc"] == 0 for r in joined), 0, "proposition_index.csv")
    checks.add("sentences.literal_substring", all(r["literal_text_matches_in_bhc"] > 0 for r in joined if r["proposition_type"] == "sentence"),
               sum(r["literal_text_matches_in_bhc"] == 0 for r in joined if r["proposition_type"] == "sentence"), 0, "proposition_index.csv")
    checks.add('sentences.within_own_parent_chunk', not sentence_chunk_errors, sentence_chunk_errors, [], 'propositions.text / parent_text_chunk')
    strata = []
    for (author, kind), rows in sorted(groups.items()):
        result = {"author_type": author, "proposition_type": kind, "n": len(rows),
                  "invalid": sum(row[3]["invalid"] for row in rows),
                  "three_raters_agree": sum(row[3]["initial_agreement"] == 3 for row in rows),
                  "any_initial_uncertain": sum(row[3]["initial_uncertain_votes"] > 0 for row in rows),
                  "literal_text_matches_zero": sum(row[3]["literal_text_matches_in_bhc"] == 0 for row in rows),
                  "literal_text_matches_one": sum(row[3]["literal_text_matches_in_bhc"] == 1 for row in rows),
                  "literal_text_matches_multiple": sum(row[3]["literal_text_matches_in_bhc"] > 1 for row in rows)}
        pairs = sum(sum(g[f"verdict{i}"] == g[f"verdict{j}"] for i, j in ((1, 2), (1, 3), (2, 3))) for _, g, _, _ in rows)
        result["clinician_pairwise_agreement"] = pairs / (3 * len(rows))
        for label in LABELS:
            result[label] = sum(g["human_gt"] == label for _, g, _, _ in rows)
            result["valid_" + label] = sum(g["human_gt"] == label and not row["invalid"] for _, g, _, row in rows)
        strata.append(result)
    doc_rows, doc_errors = [], []
    for key, rows in sorted(documents.items()):
        first = rows[0]
        texts = {r["brief_hospital_course"] for r in rows}
        if len(texts) != 1:
            doc_errors.append(key)
        covered = bytearray(len(first["brief_hospital_course"]))
        for row in rows:
            if row["proposition_type"] == "sentence":
                for pos in literal_positions(first["brief_hospital_course"], row["text"]):
                    covered[pos:pos+len(row["text"])] = b"\1" * len(row["text"])
        uncovered = sum(not flag and not char.isspace() for flag, char in zip(covered, first["brief_hospital_course"]))
        doc_rows.append({"document_key": key, "subject_id": integer_id(first["subject_id"]),
                         "hadm_id": integer_id(first["hadm_id"]), "author_type": first["author_type"],
                         "bhc_sha256": digest_text(first["brief_hospital_course"]),
                         "bhc_characters": len(first["brief_hospital_course"]),
                         "source_row_id": integer_id(first["row_id"]),
                         "parent_chunks": len({r["parent_text_chunk"] for r in rows}),
                         "sentences": sum(r["proposition_type"] == "sentence" for r in rows),
                         "claims": sum(r["proposition_type"] == "claim" for r in rows),
                         "uncovered_nonwhitespace_characters": uncovered})
    checks.add("documents.one_bhc_per_patient_admission_author", not doc_errors, doc_errors, [], "document_index.csv")
    doc_author_sets = {sid: {r["author_type"] for r in doc_rows if r["subject_id"] == sid} for sid in patients}
    checks.add("documents.paired_authors", all(s == {"human", "llm"} for s in doc_author_sets.values()) and len(doc_rows) == 2 * len(patients),
               len(doc_rows), 2*len(patients), "document_index.csv")
    checks.add("documents.sentence_coverage", all(r["uncovered_nonwhitespace_characters"] == 0 for r in doc_rows),
               sum(r["uncovered_nonwhitespace_characters"] for r in doc_rows), 0, "document_index.csv (union of all literal matches; ambiguous matches not resolved)")
    missing_granularities = [r['document_key'] for r in doc_rows if not r['sentences'] or not r['claims']]
    checks.add('documents.both_proposition_granularities', not missing_granularities, missing_granularities, [], 'document_index.csv')

    text_groups = defaultdict(list)
    for row in ps:
        text_groups[row["text"]].append(row)
    for text, rows in text_groups.items():
        if len(rows) > 1:
            overlap.append({"text_sha256": digest_text(text), "rows": len(rows),
                            "patients": len({r["subject_id"] for r in rows}),
                            "documents": len({(r["subject_id"], r["author_type"]) for r in rows}),
                            "proposition_ids": "|".join(sorted(r["proposition_id"] for r in rows))})

    target = {integer_id(r["HADM_ID"]): r for r in admissions}
    target_by_patient = defaultdict(set)
    for hadm, row in target.items():
        target_by_patient[integer_id(row["SUBJECT_ID"])].add(hadm)
    checks.add("admissions.one_target_per_patient", all(len(x) == 1 for x in target_by_patient.values()),
               dict(Counter(len(x) for x in target_by_patient.values())), "one", "admissions.csv.gz")
    admission_errors, admission_conflicts = [], []
    for p in ps:
        admission = target.get(integer_id(p["hadm_id"]))
        if admission is None or integer_id(admission["SUBJECT_ID"]) != integer_id(p["subject_id"]):
            admission_errors.append(p["proposition_id"])
            continue
        for field, value in [("ADMITTIME",p["admitdate"]+" "+p["admittime"]),("DISCHTIME",p["dischargedate"]+" "+p["dischargetime"])]:
            if value != admission[field]:
                admission_conflicts.append({"proposition_id":p["proposition_id"],"subject_id":integer_id(p["subject_id"]),
                                            "hadm_id":integer_id(p["hadm_id"]),"author_type":p["author_type"],
                                            "field":field,"propositions_value":value,"admissions_value":admission[field],
                                            "difference_seconds":(datetime.fromisoformat(value)-datetime.fromisoformat(admission[field])).total_seconds()})
    conflict_counts=Counter((r["subject_id"],r["hadm_id"],r["field"],r["propositions_value"],r["admissions_value"],r["difference_seconds"]) for r in admission_conflicts)
    conflict_summary=[dict(zip(("subject_id","hadm_id","field","propositions_value","admissions_value","difference_seconds","propositions"),(*key,n))) for key,n in sorted(conflict_counts.items())]
    checks.add("admissions.proposition_patient_identity", not admission_errors, admission_errors, [], "propositions / admissions")
    checks.add("admissions.timestamp_metadata_agreement", not admission_conflicts,
               {"affected_propositions":len({r['proposition_id'] for r in admission_conflicts}),"patients":len({r['subject_id'] for r in admission_conflicts})},
               "matching duplicated admission/discharge timestamps", "admission_metadata_conflicts.csv", "warning")
    note_rows, time_rows = [], []
    for note in notes:
        sid, hadm = integer_id(note["SUBJECT_ID"]), integer_id(note["HADM_ID"])
        target_ids = target_by_patient[sid]
        target_admission = target[next(iter(target_ids))]
        start, end = (datetime.fromisoformat(target_admission[f]) for f in ("ADMITTIME", "DISCHTIME"))
        chartdate = datetime.fromisoformat(note["CHARTDATE"])
        row = {f: note[f] for f in note if f != "TEXT"}
        row.update({"SUBJECT_ID": sid, "HADM_ID": hadm, "scope": "target" if hadm in target_ids else "missing_hadm" if hadm is None else "other",
                    "text_sha256": digest_text(note["TEXT"]), "text_characters": len(note["TEXT"]),
                    "inside_target_calendar_dates": start.date() <= chartdate.date() <= end.date()})
        for field in ("CHARTTIME", "STORETIME"):
            stamp = datetime.fromisoformat(note[field]) if note[field] else None
            if stamp and (stamp > end or (hadm in target_ids and stamp < start)):
                time_rows.append({"ROW_ID": note["ROW_ID"], "subject_id": sid, "hadm_id": hadm,
                                  "field": field, "timestamp": note[field],
                                  "issue": "after_target_discharge" if stamp > end else "before_target_admission",
                                  "difference_seconds": (stamp-end).total_seconds() if stamp > end else (stamp-start).total_seconds()})
        if note["CHARTTIME"] and chartdate.date() != datetime.fromisoformat(note["CHARTTIME"]).date():
            time_rows.append({"ROW_ID": note["ROW_ID"], "subject_id": sid, "hadm_id": hadm,
                              "field": "CHARTDATE", "timestamp": note["CHARTDATE"],
                              "issue": "chartdate_differs_from_charttime_date", "difference_seconds": None})
        note_rows.append(row)
    note_hadm_patients = defaultdict(set)
    for r in note_rows:
        if r["HADM_ID"]:
            note_hadm_patients[r["HADM_ID"]].add(r["SUBJECT_ID"])
    checks.add("ehr.admission_patient_consistency", all(len(s) == 1 for s in note_hadm_patients.values()),
               [k for k, s in note_hadm_patients.items() if len(s) != 1], [], "ehr_note_index.csv")
    known_admission_mismatches = [r['ROW_ID'] for r in note_rows if r['HADM_ID'] in target
                                 and r['SUBJECT_ID'] != integer_id(target[r['HADM_ID']]['SUBJECT_ID'])]
    checks.add('ehr.known_admission_patient_matches_admissions', not known_admission_mismatches,
               known_admission_mismatches, [], 'ehr_noteevents / admissions; only released ADMISSIONS rows')
    human_sources = {r["source_row_id"] for r in doc_rows if r["author_type"] == "human"}
    source_leaks = sorted(human_sources & {r["ROW_ID"] for r in notes})
    target_dc = [r["ROW_ID"] for r in note_rows if r["scope"] == "target" and r["CATEGORY"].strip().lower() == "discharge summary"]
    checks.add("ehr.target_discharge_summary_excluded", not source_leaks and not target_dc,
               {"source_note_overlap": source_leaks, "target_discharge_notes": target_dc},
               "no target discharge summary", "document_index.csv / ehr_note_index.csv")
    patient_rows = []
    for sid in sorted(patients, key=int):
        ns = [r for r in note_rows if r["SUBJECT_ID"] == sid]
        pp = [r for r in joined if r["subject_id"] == sid]
        target_hadm = next(iter(target_by_patient[sid]))
        patient_rows.append({"subject_id": sid, "target_hadm_id": target_hadm,
                             "admittime": target[target_hadm]["ADMITTIME"], "dischtime": target[target_hadm]["DISCHTIME"],
                             "ehr_notes": len(ns), "target_notes": sum(r["scope"] == "target" for r in ns),
                             "other_admission_notes": sum(r["scope"] == "other" for r in ns),
                             "reference_admissions": len({r["HADM_ID"] for r in ns if r["HADM_ID"]}),
                             "ehr_characters": sum(r["text_characters"] for r in ns),
                             "target_physician_notes": sum(r["CATEGORY"] == "Physician" and r["scope"] == "target" for r in ns),
                             "propositions": len(pp), "invalid": sum(r["invalid"] for r in pp),
                             **{label: sum(r["human_gt"] == label for r in pp) for label in LABELS}})
    validity = {f: sum(r[f] == "True" for r in vs) for f in flag_fields}
    validity["final_vs_draft_disagreements"] = {f: sum(r[f] != r[f+"_draft"] for r in vs)
                                              for f in ("imperative", "interrogative", "incomplete", "vague")}
    summary = {"propositions": len(ps), "patients": len(patients), "target_admissions": len(target),
               "documents": len(doc_rows), "parent_chunk_groups": sum(r["parent_chunks"] for r in doc_rows),
               "unique_proposition_texts": len(text_groups), "duplicate_text_extra_rows": len(ps)-len(text_groups),
               "admission_metadata_conflicts":conflict_summary,
               "source_row_ids":{a:{"nonempty_propositions":sum(bool(r['row_id']) for r in ps if r['author_type']==a),
                                    "unique_nonempty":len({r['row_id'] for r in ps if r['author_type']==a and r['row_id']})} for a in ("human","llm")},
               "cross_patient_duplicate_text_groups": sum(r["patients"] > 1 for r in overlap),
               "strata": strata, "human_gt": dict(Counter(r["human_gt"] for r in hs)),
               "validity": validity, "first_round_raters": sorted(annotators),
               "first_round_agreement_counts": dict(agreement_counts), "round2_decisions": dict(round2_counts),
               "later_raters": sorted({r[f] for r in hs for f in ("rater4", "rater5") if r[f]}),
               "adjudicated_rows": sum(bool(r["adjudicated_verdict"]) for r in hs),
               "second_round_anomalies": round2_details,
               "second_round_votes_equal": sum(r['verdict4'] == r['verdict5'] for r in hs if r['round1_num_raters_agree'] == '0'),
               "second_round_votes_different": sum(r['verdict4'] != r['verdict5'] for r in hs if r['round1_num_raters_agree'] == '0'),
               "annotation_nonempty_fields": {f: sum(bool(r[f].strip()) for r in hs) for f in hs[0] if f.startswith("comment") or f == "adjudicated_comment"},
               "ehr_notes": len(notes), "ehr_admissions": len(note_hadm_patients),
               "ehr_target_notes": sum(r["scope"] == "target" for r in note_rows),
               "ehr_other_notes": sum(r["scope"] == "other" for r in note_rows),
               "patients_with_other_admissions": sum(r["other_admission_notes"] > 0 for r in patient_rows),
               "other_admission_ids": sorted(set(note_hadm_patients)-set(target), key=int),
               "ehr_categories": dict(Counter(r["CATEGORY"] for r in notes)),
               "ehr_unique_texts": len({r["TEXT"] for r in notes}),
               "discharge_note_scopes": dict(Counter(r["scope"] for r in note_rows if r["CATEGORY"].strip().lower() == "discharge summary")),
               "temporal_issues": dict(Counter(r["field"]+":"+r["issue"] for r in time_rows)),
               "patient_distributions": {f: distribution([r[f] for r in patient_rows]) for f in ("ehr_notes", "ehr_characters", "propositions")},
               "document_distributions": {a: {f: distribution([r[f] for r in doc_rows if r["author_type"] == a]) for f in ("bhc_characters", "sentences", "claims", "parent_chunks")} for a in ("human", "llm")}}
    checks.add("ehr.timestamp_caveats", not time_rows, summary["temporal_issues"], {}, "temporal_anomalies.csv", "warning")
    checks.add("ehr.minimum_note_criteria", all(r["ehr_notes"] >= 10 and r["target_physician_notes"] >= 2 for r in patient_rows),
               {"min_notes": min(r["ehr_notes"] for r in patient_rows), "min_target_physician": min(r["target_physician_notes"] for r in patient_rows)},
               "at least 10 EHR notes and 2 target physician notes", "patient_index.csv", "warning")
    exports.update({"proposition_index": joined, "document_index": doc_rows, "patient_index": patient_rows,
                    "admission_metadata_conflicts":admission_conflicts,"admission_conflict_summary":conflict_summary,
                    "label_distribution": strata, "duplicate_proposition_text_groups": sorted(overlap, key=lambda r:r["text_sha256"]),
                    "annotation_anomalies": annotation_errors, "validity_anomalies": validity_errors,
                    "second_round_anomalies": round2_details,
                    "ehr_note_index": note_rows, "temporal_anomalies": time_rows})
    return summary, exports, joined
