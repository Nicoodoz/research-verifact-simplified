"""Small, deterministic helpers shared by the audit and its tests."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

LABELS = ("Supported", "Not Supported", "Not Addressed")
CONFIG_FIELDS = (
    "fact_type", "retrieval_method", "top_n", "reference_format",
    "reference_only_admission", "deduplicate_text",
)
PRELIMINARY_MODELS = {"R1-8B", "R1-70B", "Llama-8B", "Llama-70B"}
CSV_FILES = {
    "propositions": "propositions/propositions.csv.gz",
    "human_verdicts": "propositions/human_verdicts.csv.gz",
    "proposition_validity": "propositions/proposition_validity.csv.gz",
    "ehr_noteevents": "reference_ehr/ehr_noteevents.csv.gz",
    "admissions": "reference_ehr/admissions.csv.gz",
    "model_metadata": "verifact/model_metadata.csv",
    "rater_configurations": "verifact/rater_configurations.csv",
    "experiment_matrix": "verifact/experiment_matrix.csv",
}


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Preserve CSV strings (including blanks and decimal-looking IDs)."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)):
            raise ValueError(f"Missing or duplicate CSV headers: {path}")
        rows = list(reader)
    if any(None in row or any(v is None for v in row.values()) for row in rows):
        raise ValueError(f"Ragged CSV row: {path}")
    return fields, rows


def integer_id(value: str) -> str | None:
    """Canonicalize only integral IDs: '183959.0' -> '183959'; blank -> None."""
    if not value.strip():
        return None
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Non-numeric ID: {value!r}") from exc
    if not number.is_finite() or number != number.to_integral_value():
        raise ValueError(f"Non-integral ID: {value!r}")
    return str(int(number))


def majority(votes: list[str]) -> tuple[int, str | None]:
    """Three-way ties have agreement count 0, matching release semantics."""
    counts = Counter(votes)
    if len(votes) != 3 or any(v not in LABELS for v in votes):
        raise ValueError("Expected three valid clinician votes")
    label, count = counts.most_common(1)[0]
    return (count, label) if count >= 2 else (0, None)


def literal_positions(text: str, needle: str) -> list[int]:
    if not needle:
        return []
    positions, start = [], 0
    while (start := text.find(needle, start)) >= 0:
        positions.append(start)
        start += 1
    return positions


def distribution(values: list[int | float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    def quantile(q: float) -> float:
        index = (len(ordered) - 1) * q
        lo, hi = math.floor(index), math.ceil(index)
        return ordered[lo] + (ordered[hi] - ordered[lo]) * (index - lo)
    return {"n": len(values), "min": ordered[0], "p25": quantile(.25),
            "median": quantile(.5), "p75": quantile(.75), "p95": quantile(.95),
            "max": ordered[-1], "mean": sum(values) / len(values)}


def csv_profile(fields: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    columns = []
    for field in fields:
        counts = Counter(row[field] for row in rows)
        lengths = [len(row[field]) for row in rows]
        columns.append({"name": field, "type": "CSV string (uncoerced)",
                        "null_count": 0, "empty_count": counts.get("", 0),
                        "whitespace_only_count": sum(n for v, n in counts.items() if v and not v.strip()),
                        "distinct_count_including_empty": len(counts),
                        "min_characters": min(lengths, default=0),
                        "max_characters": max(lengths, default=0),
                        "values": dict(sorted(counts.items())) if len(counts) <= 15 and max(lengths, default=0) <= 150 else None})
    row_counts = Counter(tuple(row[f] for f in fields) for row in rows)
    return {"rows": len(rows), "columns": columns,
            "exact_duplicate_extra_rows": sum(n - 1 for n in row_counts.values())}


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, key: str, ok: bool | None, observed: Any, expected: Any,
            evidence: str, severity: str = "error") -> None:
        if any(row["id"] == key for row in self.rows):
            raise ValueError(f"Duplicate check ID: {key}")
        status = "unverified" if ok is None else "pass" if ok else "fail" if severity == "error" else "warning"
        self.rows.append({"id": key, "status": status, "observed": observed,
                          "expected": expected, "evidence": evidence})

    @property
    def failed(self) -> bool:
        return any(row["status"] == "fail" for row in self.rows)


def write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else ["no_rows"]
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def new_run(output_root: Path, run_name: str | None, raw_root: Path) -> Path:
    """Never overwrite a run, and never create output inside the raw tree."""
    output_root, raw_root = output_root.resolve(), raw_root.resolve()
    if output_root == raw_root or raw_root in output_root.parents:
        raise ValueError("Audit output cannot be inside data/00_raw")
    if run_name is not None and (not run_name or Path(run_name).name != run_name or run_name in {".", ".."}):
        raise ValueError("run_name must be one directory name")
    output_root.mkdir(parents=True, exist_ok=True)
    if run_name is not None:
        result = output_root / run_name
        if raw_root in result.resolve().parents or result.resolve() == raw_root:
            raise ValueError("Resolved run directory cannot be inside raw data")
        result.mkdir(exist_ok=False)
        return result
    number = 1
    while True:
        result = output_root / f"run_{number:03d}"
        try:
            result.mkdir(exist_ok=False)
            return result
        except FileExistsError:
            number += 1
