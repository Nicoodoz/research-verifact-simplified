"""Inventory, checksums, archive integrity, and source-document evidence."""

from __future__ import annotations

import io
import re
import tarfile
from pathlib import Path, PurePosixPath

from pypdf import PdfReader

from .common import Checks, digest_file, digest_text


def parse_checksums(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"([0-9a-f]{64})\s+\*?(.+)", line)
        if not match:
            raise ValueError(f"Malformed SHA256SUMS entry: {line!r}")
        digest, name = match.groups()
        posix = PurePosixPath(name)
        if posix.is_absolute() or ".." in posix.parts or "\\" in name or ":" in name:
            raise ValueError(f"Unsafe checksum path: {name!r}")
        if name in result:
            raise ValueError(f"Duplicate checksum path: {name}")
        result[name] = digest
    return result


def inventory(base: Path, checks: Checks) -> tuple[list[dict], dict[str, str]]:
    declared = parse_checksums((base / "SHA256SUMS.txt").read_text(encoding="utf-8"))
    paths = sorted(p for p in base.rglob("*") if p.is_file())
    rows = []
    for path in paths:
        name = path.relative_to(base).as_posix()
        rows.append({"path": name, "bytes": path.stat().st_size,
                     "sha256": digest_file(path), "manifest_sha256": declared.get(name),
                     "manifest_match": None, "is_symlink": path.is_symlink()})
        if name in declared:
            rows[-1]["manifest_match"] = rows[-1]["sha256"] == declared[name]
    actual = {r["path"] for r in rows}
    missing = sorted(set(declared) - actual)
    mismatches = [r["path"] for r in rows if r["manifest_match"] is False]
    unlisted = sorted(actual - set(declared) - {"SHA256SUMS.txt"})
    checks.add("release.manifest_files_present", not missing, missing, [], "file_inventory.csv / SHA256SUMS.txt")
    checks.add("release.manifest_hashes_match", not mismatches, mismatches, [], "file_inventory.csv")
    checks.add("release.no_unlisted_files", not unlisted, unlisted, [], "file_inventory.csv", "warning")
    return rows, {r["path"]: r["sha256"] for r in rows}


def inspect_archives(base: Path, patients: set[str], checks: Checks, progress=lambda _: None) -> tuple[list[dict], list[dict]]:
    archive_rows, pdf_rows = [], []
    for path in sorted(base.rglob("*.tar.gz")):
        progress(f"Inspect archive {path.name}")
        with tarfile.open(path, "r:gz") as archive:
            seen = set()
            for member in archive:
                row = {"archive": path.relative_to(base).as_posix(), "member": member.name,
                       "kind": "file" if member.isfile() else "directory" if member.isdir() else "other",
                       "bytes": member.size, "sha256": None, "utf8_decodable": None}
                if member.name in seen:
                    checks.add(f"archive.duplicate.{member.name}", False, member.name, "unique", row["archive"])
                seen.add(member.name)
                if member.isfile():
                    handle = archive.extractfile(member)
                    if handle is None:
                        raise ValueError(f"Unreadable archive member: {member.name}")
                    content = handle.read()
                    import hashlib
                    row["sha256"] = hashlib.sha256(content).hexdigest()
                    if member.name.endswith(".txt"):
                        content.decode("utf-8")
                        row["utf8_decodable"] = True
                    if member.name.endswith(".pdf"):
                        reader = PdfReader(io.BytesIO(content))
                        pdf_rows.append({"member": member.name, "subject_id": PurePosixPath(member.name).stem,
                                         "pages": len(reader.pages), "encrypted": reader.is_encrypted,
                                         "sha256": row["sha256"]})
                        if len(pdf_rows) % 25 == 0:
                            progress(f"Parsed {len(pdf_rows)} reference PDFs")
                archive_rows.append(row)
    pdf_subjects = {r["subject_id"] for r in pdf_rows}
    checks.add("reference_pdf.patient_coverage", pdf_subjects == patients and len(pdf_rows) == len(patients),
               {"pdf_files": len(pdf_rows), "missing": sorted(patients - pdf_subjects),
                "extra": sorted(pdf_subjects - patients)}, "one PDF per subject", "pdf_inventory.csv")
    checks.add("reference_pdf.content_equivalence", None,
               "Archive members, PDF structure/page counts and patient filenames checked; clinical text equivalence not checked",
               "Doctor-view PDF clinical content equals CSV reference notes", "pdf_inventory.csv")
    return archive_rows, pdf_rows


def source_evidence(base: Path, paper: Path, checks: Checks) -> dict:
    """Capture short, page-addressable evidence; never write to the source PDF."""
    readme = (base / "README.md").read_text(encoding="utf-8")
    missing_docs = [name for name in ("verifact-bhc-croissant.jsonld", "verifact/coverage.csv",
                                     "verifact/missing_verdict_keys.csv")
                    if name in readme and not (base / name).exists()]
    checks.add("documentation.readme_declared_files", not missing_docs, missing_docs, [],
               "Local release README file tree / Version 1.1.0 scope", "warning")
    reader = PdfReader(paper)
    needles = {"population": (1, "13,070"), "dataset_counts": (5, "9095"),
               "round1_disagreement": (5, "478"), "clinician_agreement_table": (6, "88.5%"),
               "annotation_flow": (4, "three-way"),
               "decomposition": (2, "Natural Language Toolkit")}
    evidence = {}
    for key, (page, needle) in needles.items():
        content = reader.pages[page - 1].extract_text().replace("\u00ad", "")
        offset = content.find(needle)
        evidence[key] = {"page": page, "needle": needle, "located": offset >= 0,
                         "excerpt": content[max(0, offset - 200):offset + 420] if offset >= 0 else None}
        checks.add(f"source.paper_anchor.{key}", offset >= 0, evidence[key]["located"], True,
                   f"docs/sources/VeriFact.pdf page {page}", "warning")
    return {"readme_sha256": digest_file(base / "README.md"), "paper_sha256": digest_file(paper),
            "paper_pages": len(reader.pages), "paper_evidence": evidence,
            "readme_absent_files": missing_docs,
            "scope": "Counts and schema claims checked below; generation lineage, clinical correctness, supplementary analyses and PDF text equivalence are not certified."}
