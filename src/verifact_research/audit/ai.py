"""Stream released Parquet files; reconstruct expected AI coverage from metadata."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import json
from pathlib import Path

import duckdb

from .common import CONFIG_FIELDS, LABELS, PRELIMINARY_MODELS, Checks


def query(db, sql: str, parameters=None) -> list[dict]:
    cursor = db.execute(sql, parameters or [])
    names = [c[0] for c in cursor.description]
    return [dict(zip(names, row)) for row in cursor.fetchall()]


def scalar(db, sql: str):
    return db.execute(sql).fetchone()[0]


def insert_dicts(db, name: str, rows: list[dict]) -> None:
    fields = list(rows[0])
    quote = lambda value: '"' + value.replace('"', '""') + '"'
    db.execute(f"CREATE TABLE {name} (" + ",".join(quote(f) + " VARCHAR" for f in fields) + ")")
    # Bulk in-memory JSON import avoids a transaction per Python row. No temp files.
    values = [{f: None if row[f] is None else str(row[f]) for f in fields} for row in rows]
    paths = ['$.' + json.dumps(f) for f in fields]
    db.execute(f"INSERT INTO {name} SELECT " + ",".join("json_extract_string(value, ?)" for _ in fields) +
               " FROM json_each(?)", paths + [json.dumps(values, ensure_ascii=False)])


def expected_configurations(raters: list[dict], matrix: list[dict], models: list[str]) -> tuple[list[dict], list[dict]]:
    """A matrix row includes author/proposition strata; a rater alias does not."""
    lookup = {}
    for r in raters:
        key = (r["model"], *(r[f] for f in CONFIG_FIELDS))
        if key in lookup:
            raise ValueError("Duplicate model/retrieval configuration")
        lookup[key] = r["rater_alias"]
    pairs, errors = [], []
    for number, entry in enumerate(matrix, 1):
        role = entry["publication_role"]
        if role not in {"main", "preliminary_sensitivity"}:
            errors.append({"matrix_row": number, "issue": "unknown publication role", "model": ""})
            continue
        for model in sorted(models):
            if role == "preliminary_sensitivity" and model not in PRELIMINARY_MODELS:
                continue
            key = (model, *(entry[f] for f in CONFIG_FIELDS))
            if key not in lookup:
                errors.append({"matrix_row": number, "issue": "missing rater for permitted pair", "model": model})
                continue
            pairs.append({"matrix_row": number, "model": model, "rater_alias": lookup[key], **entry})
    return pairs, errors


def classify_reference_header(row: dict) -> dict:
    """Compare absolute dates only; relative-time and score formats are distinct."""
    result = {**row, "header_present": bool(row["reference_start"] and row["reference_end"]),
              "matches_propositions": None, "matches_admissions": None}
    format_name = row["reference_format"]
    if format_name == "relative_time":
        result["comparison_status"] = "relative_time_not_compared"
    elif format_name == "score":
        result["comparison_status"] = "score_not_applicable"
    elif format_name != "absolute_time":
        result["comparison_status"] = "unknown_reference_format"
    else:
        fields = ("reference_start", "reference_end", "proposition_admittime",
                  "proposition_dischtime", "admissions_admittime", "admissions_dischtime")
        try:
            dates = {field: datetime.fromisoformat(row[field]) for field in fields}
        except (ValueError, TypeError):
            result["comparison_status"] = "unparseable_absolute"
        else:
            result["comparison_status"] = "compared_absolute"
            for name in ("propositions", "admissions"):
                prefix = "proposition" if name == "propositions" else name
                result["matches_" + name] = (dates["reference_start"] == dates[prefix + "_admittime"]
                                              and dates["reference_end"] == dates[prefix + "_dischtime"])
    return result


def parquet_profile(db, name: str, progress) -> dict:
    columns = query(db, f"DESCRIBE {name}")
    profile = {"rows": scalar(db, f"SELECT count(*) FROM {name}"), "columns": []}
    for col in columns:
        field = col["column_name"]
        progress(f"profile {name}.{field}")
        q = '"' + field.replace('"', '""') + '"'
        # SHA-256 keeps exact-content distinctness practical for long explanations.
        # Not an approximate-count algorithm; cryptographic collision resistance is assumed.
        count = query(db, f"""SELECT count(*) FILTER (WHERE {q} IS NULL) AS null_count,
            count(*) FILTER (WHERE {q} = '') AS empty_count,
            count(*) FILTER (WHERE {q} <> '' AND regexp_full_match({q}, '\\s*')) AS whitespace_only_count,
            count(DISTINCT sha256({q})) AS distinct_nonnull_sha256,
            min(length({q})) AS min_characters, max(length({q})) AS max_characters
            FROM {name}""")[0]
        profile["columns"].append({"name": field, "type": col["column_type"],
                                   "distinct_method": "distinct SHA-256 of non-null UTF-8 content", **count})
    return profile


def audit_ai(base: Path, tables: dict, propositions: list[dict], checks: Checks,
             progress, memory_limit: str = "2GB") -> tuple[dict, dict, dict]:
    raters, matrix, models = (tables[n] for n in ("rater_configurations", "experiment_matrix", "model_metadata"))
    expected, config_errors = expected_configurations(raters, matrix, [r["model"] for r in models])
    checks.add("matrix.rater_resolution", not config_errors, config_errors, [], "experiment_matrix / rater_configurations")
    signatures = [(r["model"], r["rater_alias"], r["author_type"], r["proposition_type"]) for r in expected]
    checks.add("matrix.unique_permitted_pairs", len(signatures) == len(set(signatures)),
               len(signatures)-len(set(signatures)), 0, "expected_model_configurations.csv")
    if len(signatures) != len(set(signatures)) or not expected:
        raise ValueError("Ambiguous or empty expected configuration matrix")
    model_names = {r["model"] for r in models}
    bad_raters = [r["rater_alias"] for r in raters if r["model"] not in model_names]
    checks.add("fk.raters.models", not bad_raters, bad_raters, [], "rater_configurations / model_metadata")
    expected_names = [r["rater_alias"] for r in raters if r["rater_name"] != "model="+r["model"]+","+",".join(f"{f}={r[f]}" for f in CONFIG_FIELDS)]
    checks.add("raters.name_fields_agree", not expected_names, expected_names, [], "rater_configurations.csv")

    db = duckdb.connect(config={"memory_limit": memory_limit, "threads": 2, "temp_directory": ""})
    db.execute("SET enable_progress_bar=false")
    try:
        db.read_parquet(str(base/"verifact/verdicts.parquet")).create_view("verdicts")
        db.read_parquet(str(base/"verifact/reference_payloads.parquet")).create_view("refs")
        p_fields=("proposition_id","subject_id","hadm_id","author_type","proposition_type","human_gt","invalid",
                  "proposition_admittime","proposition_dischtime","admissions_admittime","admissions_dischtime")
        insert_dicts(db, "p", [{k:r.get(k) for k in p_fields} for r in propositions])
        insert_dicts(db, "r", raters)
        insert_dicts(db, "m", models)
        insert_dicts(db, "c", expected)
        db.execute("""CREATE VIEW expected_keys AS SELECT p.proposition_id,c.rater_alias,c.model,
            c.matrix_row,c.publication_role,c.author_type,c.proposition_type
            FROM c JOIN p ON c.author_type=p.author_type AND c.proposition_type=p.proposition_type""")
        progress("Parquet fields and missingness")
        profiles = {"verdicts": parquet_profile(db, "verdicts", progress), "reference_payloads": parquet_profile(db, "refs", progress)}
        for table, fields, name in [("verdicts", "proposition_id,rater_alias", "verdicts"), ("refs", "reference_id", "references")]:
            duplicate = scalar(db, f"SELECT coalesce(sum(n-1),0)::BIGINT FROM (SELECT count(*) n FROM {table} GROUP BY {fields} HAVING count(*)>1)")
            checks.add(f"keys.{name}.unique", duplicate == 0, duplicate, 0, f"{name} primary key")
        for field, target, target_field in [("proposition_id", "p", "proposition_id"), ("rater_alias", "r", "rater_alias"),
                                            ("model", "m", "model"), ("reference_id", "refs", "reference_id")]:
            missing = scalar(db, f"SELECT count(*) FROM verdicts v WHERE NOT EXISTS (SELECT 1 FROM {target} t WHERE v.{field}=t.{target_field})")
            checks.add(f"fk.verdicts.{field}", missing == 0, missing, 0, "Parquet foreign-key anti-join")
        mismatch = scalar(db, "SELECT count(*) FROM verdicts v JOIN r USING(rater_alias) WHERE v.model<>r.model")
        checks.add("verdicts.rater_model_agreement", mismatch == 0, mismatch, 0, "verdicts / raters")
        bad_label = scalar(db, "SELECT count(*) FROM verdicts WHERE verdict IS NULL OR verdict NOT IN ('Supported','Not Supported','Not Addressed')")
        checks.add("domains.ai_verdict", bad_label == 0, bad_label, 0, "verdicts.verdict")
        progress("Reference hashes and reverse foreign keys")
        wrong_hash = scalar(db, "SELECT count(*) FROM refs WHERE reference_id IS NULL OR reference IS NULL OR reference_id<>sha256(reference)")
        checks.add("references.content_sha256", wrong_hash == 0, wrong_hash, 0, "all reference payloads; exact UTF-8 text")
        orphan_refs = scalar(db, "SELECT count(*) FROM refs t WHERE NOT EXISTS (SELECT 1 FROM verdicts v WHERE v.reference_id=t.reference_id)")
        checks.add("references.all_referenced", orphan_refs == 0, orphan_refs, 0, "references / verdicts reverse anti-join")
        for name,key in (("r","rater_alias"),("m","model")):
            unused=query(db,f"SELECT {key} FROM {name} t WHERE NOT EXISTS (SELECT 1 FROM verdicts v WHERE v.{key}=t.{key}) ORDER BY 1")
            checks.add(f"coverage.metadata_{key}_used",not unused,unused,[],"metadata / verdicts reverse anti-join")

        progress("Expected versus observed AI keys")
        missing_keys = query(db, """SELECT e.model,e.rater_alias,e.proposition_id,e.matrix_row,e.publication_role,
            e.author_type,e.proposition_type,p.subject_id,p.hadm_id,p.human_gt,p.invalid
            FROM expected_keys e JOIN p USING(proposition_id)
            WHERE NOT EXISTS (SELECT 1 FROM verdicts v WHERE v.proposition_id=e.proposition_id AND v.rater_alias=e.rater_alias AND v.model=e.model)
            ORDER BY e.model,e.rater_alias,e.proposition_id""")
        unexpected = query(db, """SELECT v.model,v.rater_alias,v.proposition_id FROM verdicts v WHERE NOT EXISTS
            (SELECT 1 FROM expected_keys e WHERE v.proposition_id=e.proposition_id AND v.rater_alias=e.rater_alias AND v.model=e.model)
            ORDER BY 1,2,3""")
        checks.add("coverage.no_unexpected_verdicts", not unexpected, len(unexpected), 0, "unexpected_verdict_keys.csv")
        checks.add("coverage.no_missing_verdicts", not missing_keys, len(missing_keys), 0, "missing_verdict_keys.csv", "warning")
        coverage = query(db, """WITH expected_counts AS (
            SELECT model,rater_alias,matrix_row,author_type,proposition_type,publication_role,count(*) expected
            FROM expected_keys GROUP BY ALL), observed_counts AS (
            SELECT v.model,v.rater_alias,p.author_type,p.proposition_type,count(*) observed
            FROM verdicts v JOIN p USING(proposition_id) GROUP BY ALL)
            SELECT e.*,coalesce(o.observed,0) observed,e.expected-coalesce(o.observed,0) missing
            FROM expected_counts e LEFT JOIN observed_counts o USING(model,rater_alias,author_type,proposition_type)
            ORDER BY model,CAST(matrix_row AS INTEGER)""")
        null_reason = query(db, """SELECT model,rater_alias,proposition_id,reference_id FROM verdicts
            WHERE reason IS NULL OR regexp_full_match(reason,'\\s*') ORDER BY 1,2,3""")
        checks.add("verdicts.explanations_present", not null_reason, len(null_reason), 0, "empty_reasons.csv (README mentions one exception)", "warning")
        by_model = query(db, """SELECT v.model,count(*) verdict_rows,count(DISTINCT proposition_id) propositions,
            count(DISTINCT rater_alias) raters,
            count(*) FILTER(WHERE reason IS NULL OR regexp_full_match(reason,'\\s*')) empty_reason,
            count(*) FILTER(WHERE reasoning_chain IS NULL OR regexp_full_match(reasoning_chain,'\\s*')) empty_reasoning_chain,
            count(*) FILTER(WHERE reasoning_final_answer IS NULL OR regexp_full_match(reasoning_final_answer,'\\s*')) empty_reasoning_final_answer
            FROM verdicts v GROUP BY v.model ORDER BY v.model""")
        by_stratum = query(db, """SELECT p.author_type,p.proposition_type,count(DISTINCT p.proposition_id) propositions,
            count(DISTINCT v.proposition_id) with_ai,count(v.proposition_id) ai_rows,
            count(DISTINCT p.proposition_id) FILTER(WHERE p.invalid='True') invalid_propositions,
            count(DISTINCT v.proposition_id) FILTER(WHERE p.invalid='True') invalid_with_ai
            FROM p LEFT JOIN verdicts v USING(proposition_id) GROUP BY 1,2 ORDER BY 1,2""")
        prediction_labels = query(db, """SELECT v.model,p.author_type,p.proposition_type,v.verdict,count(*) n
            FROM verdicts v JOIN p USING(proposition_id) GROUP BY ALL ORDER BY 1,2,3,4""")
        progress("Compare exact contexts across judges sharing retrieval settings")
        config_sql = ",".join("r."+f for f in CONFIG_FIELDS)
        db.execute(f"""CREATE TEMP TABLE context_groups AS SELECT v.proposition_id,{config_sql},
            count(DISTINCT v.model) models,count(DISTINCT v.reference_id) contexts
            FROM verdicts v JOIN r USING(rater_alias) GROUP BY ALL""")
        consistency = query(db, """SELECT fact_type,retrieval_method,top_n,reference_format,reference_only_admission,deduplicate_text,count(*) proposition_configuration_groups,
            count(*) FILTER(WHERE models>=2) multiple_model_groups,
            count(*) FILTER(WHERE models>=2 AND contexts=1) same_exact_context_groups,
            count(*) FILTER(WHERE models>=2 AND contexts>1) different_exact_context_groups,
            max(contexts) maximum_context_variants
            FROM context_groups GROUP BY fact_type,retrieval_method,top_n,reference_format,reference_only_admission,deduplicate_text
            ORDER BY fact_type,retrieval_method,CAST(top_n AS INTEGER),reference_format,reference_only_admission,deduplicate_text""")
        context_examples = query(db, "SELECT * FROM context_groups WHERE models>=2 AND contexts>1 ORDER BY proposition_id,fact_type,retrieval_method,CAST(top_n AS INTEGER),reference_format,reference_only_admission LIMIT 100")
        n_different = sum(r["different_exact_context_groups"] for r in consistency)
        checks.add("comparability.identical_contexts_across_models", n_different == 0, n_different, 0,
                   "context_consistency.csv (exact UTF-8 differences, not necessarily semantic differences)", "warning")
        lengths = query(db, """SELECT min(length(reference)) min_characters,median(length(reference)) median_characters,
            max(length(reference)) max_characters,avg(length(reference)) mean_characters FROM refs""")[0]
        usage = query(db, """SELECT uses,count(*) payloads FROM
            (SELECT reference_id,count(*) uses FROM verdicts GROUP BY 1) GROUP BY 1 ORDER BY 1""")
        progress("Compare actual reference admission headers with both metadata sources")
        header_rows=query(db,"""WITH headers AS MATERIALIZED (
            SELECT reference_id,
              regexp_extract(left(reference,400),'Hospital Admission Start: ([^\\r\\n]*)',1) reference_start,
              regexp_extract(left(reference,400),'Hospital Admission End: ([^\\r\\n]*)',1) reference_end
            FROM refs)
            SELECT p.subject_id,p.hadm_id,r.reference_format,p.proposition_admittime,p.proposition_dischtime,
                   p.admissions_admittime,p.admissions_dischtime,h.reference_start,h.reference_end,
                   count(DISTINCT h.reference_id) payloads,count(*) verdict_rows
            FROM verdicts v JOIN p USING(proposition_id) JOIN r USING(rater_alias) JOIN headers h USING(reference_id)
            GROUP BY ALL ORDER BY p.subject_id,p.hadm_id,r.reference_format,h.reference_start,h.reference_end""")
        header_rows = [classify_reference_header(row) for row in header_rows]
        header_differences = [row for row in header_rows if row['matches_admissions'] is False]
        header_missing = [row for row in header_rows if row['comparison_status'] in
                          {'unparseable_absolute', 'unknown_reference_format'}]
        header_formats = []
        for format_name in sorted({row['reference_format'] for row in header_rows}):
            group = [row for row in header_rows if row['reference_format'] == format_name]
            header_formats.append({
                'reference_format': format_name, 'header_groups': len(group),
                'verdict_rows': sum(row['verdict_rows'] for row in group),
                'compared_verdict_rows': sum(row['verdict_rows'] for row in group if row['comparison_status'] == 'compared_absolute'),
                'mismatched_admissions_verdict_rows': sum(row['verdict_rows'] for row in group if row['matches_admissions'] is False),
                'mismatched_propositions_verdict_rows': sum(row['verdict_rows'] for row in group if row['matches_propositions'] is False),
            })
        checks.add('references.header_join_preserves_verdicts', sum(row['verdict_rows'] for row in header_rows) == profiles['verdicts']['rows'],
                   sum(row['verdict_rows'] for row in header_rows), profiles['verdicts']['rows'], 'reference_admission_headers.csv')
        checks.add("references.admission_header_dates",not header_differences,
                   {"patients":len({r['subject_id'] for r in header_differences}),"verdict_rows":sum(r['verdict_rows'] for r in header_differences)},
                   "absolute_time admission header equals admissions.csv", "reference_admission_headers.csv", "warning")
        checks.add("references.parse_admission_headers",not header_missing,
                   sum(r['verdict_rows'] for r in header_missing),0,"absolute_time ISO dates in first 400 characters; relative_time/score not compared", "warning")
        source_paths = [row["source_artifact"] for row in models]
        checks.add("provenance.original_model_artifacts", None, source_paths,
                   "verify model_metadata.source_sha256 against original Feather files", "Original artifacts are not part of this release")
        summary = {"verdict_rows": profiles["verdicts"]["rows"], "reference_payloads": profiles["reference_payloads"]["rows"],
                   "models": len(models), "rater_configurations": len(raters), "experiment_matrix_rows": len(matrix),
                   "matrix_roles": dict(Counter(r["publication_role"] for r in matrix)),
                   "permitted_model_configuration_pairs": len(expected),
                   "expected_verdict_rows": sum(r["expected"] for r in coverage),
                   "missing_verdict_rows": len(missing_keys), "unexpected_verdict_rows": len(unexpected),
                   "covered_propositions": scalar(db, "SELECT count(DISTINCT proposition_id) FROM verdicts"),
                   "empty_reasons": len(null_reason), "model_coverage": by_model, "stratum_coverage": by_stratum,
                   "context_groups_with_different_payloads": n_different,
                   "context_groups_comparing_multiple_models": sum(r["multiple_model_groups"] for r in consistency),
                   "reference_header_comparisons":header_rows,
                   "reference_header_formats":header_formats,
                   "reference_header_mismatch_patients":sorted({r['subject_id'] for r in header_differences}),
                   "reference_characters": lengths, "metadata_models": models,
                   "config_value_domains": {f: sorted({r[f] for r in raters}) for f in CONFIG_FIELDS}}
        exports = {"expected_model_configurations": expected, "model_configuration_coverage": coverage,
                   "missing_verdict_keys": missing_keys, "unexpected_verdict_keys": unexpected,
                   "empty_reasons": null_reason, "model_coverage": by_model, "ai_stratum_coverage": by_stratum,
                   "ai_label_distribution": prediction_labels, "context_consistency": consistency,
                   "context_difference_examples": context_examples, "reference_reuse_distribution": usage,
                   "reference_admission_headers":header_rows,
                   "model_metadata": models, "rater_configurations": raters, "experiment_matrix": matrix}
        return summary, exports, profiles
    finally:
        db.close()
