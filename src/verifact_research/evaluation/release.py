"""Read-only release adapters; independently reconstruct cohorts and experiment pairs."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from verifact_research.audit.common import digest_file, integer_id, majority, read_csv
from .metrics import encode

CONFIG = ["fact_type", "retrieval_method", "top_n", "reference_format",
          "reference_only_admission", "deduplicate_text"]
STRATUM = ["author_type", "proposition_type"]


def unique(rows: list[dict], key: str) -> dict:
    result = {r[key]: r for r in rows}
    if len(result) != len(rows) or any(not k for k in result):
        raise ValueError(f"Nonunique or blank key: {key}")
    return result


def load_cohort(base: Path, audit: Path | None = None) -> list[dict]:
    """Preserve human_verdicts CSV order for the author's MCC bootstrap ordering."""
    props = unique(read_csv(base / "propositions/propositions.csv.gz")[1], "proposition_id")
    humans = read_csv(base / "propositions/human_verdicts.csv.gz")[1]
    hmap = unique(humans, "proposition_id")
    validity = unique(read_csv(base / "propositions/proposition_validity.csv.gz")[1], "proposition_id")
    admissions = unique(read_csv(base / "reference_ehr/admissions.csv.gz")[1], "HADM_ID")
    if set(props) != set(hmap) or set(props) != set(validity):
        raise ValueError("Proposition tables have different IDs")
    result = []
    for order, h in enumerate(humans):
        pid = h["proposition_id"]
        p, v = props[pid], validity[pid]
        for field in ["text", *STRATUM]:
            if p[field] != h[field] or p[field] != v[field]:
                raise ValueError(f"Conflicting {field}: {pid}")
        if v["invalid"] not in {"True", "False"}:
            raise ValueError(f"Invalid validity boolean: {pid}")
        votes = [h[f"verdict{i}"] for i in range(1, 4)]
        count, label = majority(votes)
        if (label if label else h["adjudicated_verdict"]) != h["human_gt"]:
            raise ValueError(f"Published final GT disagrees with majority/adjudication: {pid}")
        if count != int(h["round1_num_raters_agree"]):
            raise ValueError(f"Initial agreement mismatch: {pid}")
        subject, hadm = integer_id(p["subject_id"]), integer_id(p["hadm_id"])
        a = admissions[hadm]
        if integer_id(a["SUBJECT_ID"]) != subject:
            raise ValueError(f"Admission-patient identity mismatch: {pid}")
        time_conflict = (p["admitdate"] + " " + p["admittime"] != a["ADMITTIME"] or
                         p["dischargedate"] + " " + p["dischargetime"] != a["DISCHTIME"])
        result.append(dict(proposition_id=pid, subject_id=subject, hadm_id=hadm,
                           author_type=p["author_type"], proposition_type=p["proposition_type"],
                           human_gt=h["human_gt"], invalid=v["invalid"], initial_agreement=str(count),
                           time_metadata_conflict=str(time_conflict),
                           second_round_anomaly=str(h["round2_decision"] == "Agree" and h["verdict4"] != h["verdict5"]),
                           human_csv_order=str(order), **{f"verdict{i}": h[f"verdict{i}"] for i in range(1, 4)}))
    encode([r["human_gt"] for r in result])
    if audit is not None:
        manifest = json.loads((audit / "manifest.json").read_text(encoding="utf-8"))
        name = "proposition_index.csv"
        if digest_file(audit / name) != manifest["output_sha256"][name]:
            raise ValueError("001 proposition index hash no longer matches its historical manifest")
        previous = unique(read_csv(audit / name)[1], "proposition_id")
        if set(previous) != set(props):
            raise ValueError("Current cohort IDs disagree with 001")
        for row in result:
            for field in ["subject_id", "hadm_id", *STRATUM, "human_gt", "invalid", "initial_agreement"]:
                if row[field] != previous[row["proposition_id"]][field]:
                    raise ValueError(f"Current cohort disagrees with 001: {row['proposition_id']} {field}")
    return result


def load_predictions(base: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return narrow AI rows and independently expanded expected matrix rows.

    Clinical reference text and explanations are not materialized in this adapter.
    Configuration data remain strings to avoid ambiguous bool/ID coercion.
    """
    with duckdb.connect() as db:
        ai = db.execute("SELECT model, proposition_id, rater_alias, verdict, reference_id FROM read_parquet(?)",
                        [str(base / "verifact/verdicts.parquet")]).df()
    if ai.isna().any().any() or ai.duplicated(["model", "rater_alias", "proposition_id"]).any():
        raise ValueError("Null/duplicate AI prediction key or value")
    encode(ai["verdict"])
    raters = pd.DataFrame(read_csv(base / "verifact/rater_configurations.csv")[1])
    if raters.duplicated("rater_alias").any() or raters.duplicated(["model", *CONFIG]).any():
        raise ValueError("Nonunique rater definition")
    matrix = pd.DataFrame(read_csv(base / "verifact/experiment_matrix.csv")[1])
    if matrix.duplicated([*STRATUM, *CONFIG]).any():
        raise ValueError("Nonunique matrix definition")
    matrix["matrix_row"] = range(1, len(matrix) + 1)
    models = pd.DataFrame(read_csv(base / "verifact/model_metadata.csv")[1])["model"].tolist()
    if len(models) != len(set(models)):
        raise ValueError("Nonunique model metadata")
    expanded = matrix.merge(pd.DataFrame({"model": models}), how="cross")
    if not set(expanded.publication_role) <= {"main", "preliminary_sensitivity"}:
        raise ValueError("Unknown publication role")
    expanded = expanded.loc[(expanded.publication_role == "main") | expanded.model.isin(
        ["Llama-8B", "Llama-70B", "R1-8B", "R1-70B"])]
    expected = expanded.merge(raters.drop(columns="rater_name"), on=["model", *CONFIG],
                              how="left", validate="many_to_one", indicator=True)
    if not (expected._merge == "both").all():
        raise ValueError("Matrix configuration has no matching rater")
    expected = expected.drop(columns="_merge").sort_values(["matrix_row", "model"]).reset_index(drop=True)
    joined = ai.merge(raters[["model", "rater_alias"]], how="left", on=["model", "rater_alias"],
                      validate="many_to_one", indicator=True)
    if not (joined._merge == "both").all():
        raise ValueError("Unknown AI model/rater")
    return ai, expected
