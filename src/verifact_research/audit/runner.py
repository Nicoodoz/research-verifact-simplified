"""Task orchestration with immutable inputs and non-overwriting run directories."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import re
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .ai import audit_ai
from .cohort import audit_cohort
from .common import (CSV_FILES, Checks, csv_profile, digest_file, integer_id,
                     new_run, read_csv, write_csv, write_json)
from .release import inspect_archives, inventory, source_evidence
from .report import build_report


def compare_claims(result: dict, checks: Checks) -> list[dict]:
    c, ai = result["cohort"], result["ai"]
    rows = []
    claims = [
        ("patients", "患者数", "README; PDF p1", 100, c["patients"]),
        ("propositions", "proposition 总数", "README; PDF p5", 13070, c["propositions"]),
        ("llm", "LLM-written propositions", "PDF p5", 4445, sum(r["n"] for r in c["strata"] if r["author_type"] == "llm")),
        ("human", "human-written propositions", "PDF p5", 8625, sum(r["n"] for r in c["strata"] if r["author_type"] == "human")),
        ("claim", "atomic claim propositions", "PDF p5", 9095, sum(r["n"] for r in c["strata"] if r["proposition_type"] == "claim")),
        ("sentence", "sentence propositions", "PDF p5", 3975, sum(r["n"] for r in c["strata"] if r["proposition_type"] == "sentence")),
        ("ai_rows", "发布的 AI annotations", "README", 1437100, ai["verdict_rows"]),
        ("ai_propositions", "有 AI 结果的命题", "README", 10093, ai["covered_propositions"]),
        ("models", "Judge 模型数", "README", 9, ai["models"]),
        ("matrix", "matrix 总行数", "README", 54, ai["experiment_matrix_rows"]),
        ("pairs", "允许的 model/configuration 组合", "README", 426, ai["permitted_model_configuration_pairs"]),
        ("main", "main matrix 行数", "README", 42, ai["matrix_roles"].get("main", 0)),
        ("preliminary", "preliminary matrix 行数", "README", 12, ai["matrix_roles"].get("preliminary_sensitivity", 0)),
        ("round1_all_different", "第一轮三人完全不一致命题", "PDF p5", 478, c["first_round_agreement_counts"].get(0, 0)),
        ("empty_reason", "空 AI reason 例外数量", "README verdict schema", 1, ai["empty_reasons"]),
    ]
    for key, claim, source, expected, observed in claims:
        status = "一致" if expected == observed else "不一致"
        rows.append({"claim": claim, "source": source, "expected": expected, "observed": observed, "status": status})
        checks.add("claims."+key, expected == observed, observed, expected, source, "warning")
    for row, expected in zip(sorted(c["strata"], key=lambda r:(r["author_type"],r["proposition_type"])), [73.3, 66.9, 88.5, 84.7]):
        observed = round(row["clinician_pairwise_agreement"] * 100, 1)
        key = row["author_type"]+"_"+row["proposition_type"]
        rows.append({"claim": key+" 医生配对一致率(%)", "source":"PDF p6 Table 1", "expected":expected,
                     "observed":observed, "status":"一致" if expected == observed else "不一致"})
        checks.add("claims.clinician_agreement."+key, expected == observed, observed, expected, "PDF p6 Table 1", "warning")
    return rows


def git_info(root: Path) -> dict:
    def run(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=root, text=True, encoding="utf-8", stderr=subprocess.STDOUT).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            return f"unavailable: {exc}"
    return {"head": run("rev-parse", "HEAD"), "status_before_run": run("-c", "core.quotepath=false", "status", "--short")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only VeriFact-BHC v1.1.0 audit")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--release", type=Path, default=Path("data/00_raw/verifact-bhc/1.1.0"))
    parser.add_argument("--paper", type=Path, default=Path("docs/sources/VeriFact.pdf"))
    parser.add_argument("--output-root", type=Path, default=Path("outputs/001_dataset_audit"))
    parser.add_argument("--run-name")
    parser.add_argument("--memory-limit", default="2GB")
    args = parser.parse_args(argv)
    root = args.project_root.resolve()
    absolute = lambda path: path.resolve() if path.is_absolute() else (root/path).resolve()
    base, paper, output_root = map(absolute, (args.release, args.paper, args.output_root))
    if not base.is_dir() or not paper.is_file():
        parser.error("Release directory or source paper missing")
    if output_root == base or base in output_root.parents:
        parser.error("Output must not be inside the release directory")
    git = git_info(root)
    try:
        run = new_run(output_root, args.run_name, root/"data/00_raw")
    except (ValueError, FileExistsError) as exc:
        parser.error(str(exc))
    start = time.monotonic()
    def relative(path):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return str(path)
    code_paths = sorted(set([root/"environment.yml", root/"README.md", root/"AGENTS.md"] +
                            list((root/"src").rglob("*.py")) + list((root/"scripts").glob("*.py")) +
                            list((root/"tests").glob("*.py")) + list((root/"tasks/001_dataset_audit").glob("*.md"))))
    manifest = {"task":"001_dataset_audit", "started_utc":datetime.now(timezone.utc).isoformat(),
                "command":sys.argv, "python":sys.version, "platform":platform.platform(),
                "dependencies":{p:importlib.metadata.version(p) for p in ("duckdb", "pypdf", "fonttools")},
                "git":git, "release":relative(base), "paper":relative(paper),
                "parameters":{"memory_limit":args.memory_limit,"duckdb_threads":2,"network_used":False,"sampling":False},
                "code_and_config_sha256":{relative(p):digest_file(p) for p in code_paths if p.is_file()},
                "status":"running"}
    checks = Checks()
    with (run/"run.log").open("x", encoding="utf-8", newline="\n", buffering=1) as log:
        def progress(message):
            line = f"[{time.monotonic()-start:.1f}s] {message}"
            print(line, flush=True)
            log.write(line+"\n")
        try:
            progress("Inventory and full input checksums")
            files, before = inventory(base, checks)
            manifest["input_sha256"] = before
            manifest["paper_sha256"] = digest_file(paper)
            tables, profiles = {}, {}
            for name, rel in CSV_FILES.items():
                progress(f"Read and profile {rel}")
                fields, rows = read_csv(base/rel)
                tables[name] = rows
                profiles[name] = csv_profile(fields, rows)
            raw_subjects = (base/"reference_ehr/subject_ids.txt").read_text(encoding="utf-8-sig")
            subjects = [integer_id(x) for x in re.split(r"[\s,]+", raw_subjects.strip()) if x]
            progress("Cohort, clinician votes, validity, admissions, provenance and timestamps")
            cohort, exports, propositions = audit_cohort(tables, subjects, checks)
            progress("Archive members, PDF patient coverage and source paper")
            archives, pdfs = inspect_archives(base, set(subjects), checks, progress)
            sources = source_evidence(base, paper, checks)
            ai, ai_exports, ai_profiles = audit_ai(base, tables, propositions, checks, progress, args.memory_limit)
            profiles.update(ai_profiles)
            exports.update(ai_exports)
            exports.update({"file_inventory":files,"archive_members":archives,"pdf_inventory":pdfs})
            result = {"schema_version":"1.0", "release_version":"1.1.0", "cohort":cohort, "ai":ai,
                      "sources":sources, "inventory":files, "schemas":profiles}
            result["claim_comparisons"] = compare_claims(result, checks)
            progress("Re-read raw input checksums to verify immutability")
            after = {p.relative_to(base).as_posix():digest_file(p) for p in sorted(base.rglob("*")) if p.is_file()}
            checks.add("release.raw_unchanged", before == after,
                       sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k)), [], "full SHA-256 before versus after")
            checks.add("source.paper_unchanged", manifest["paper_sha256"] == digest_file(paper),
                       digest_file(paper), manifest["paper_sha256"], "source PDF full SHA-256 before versus after")
            result["checks"] = checks.rows
            progress("Write audit.json, tables and Chinese report")
            empty_fields = {
                "annotation_anomalies":["proposition_id","issue"], "validity_anomalies":["proposition_id","issue"],
                "second_round_anomalies":["proposition_id","issue","subject_id","hadm_id","author_type","proposition_type","rater4","rater5","verdict4","verdict5","round2_decision","adjudicated_verdict","human_gt"],
                "admission_metadata_conflicts":["proposition_id","subject_id","hadm_id","author_type","field","propositions_value","admissions_value","difference_seconds"],
                "admission_conflict_summary":["subject_id","hadm_id","field","propositions_value","admissions_value","difference_seconds","propositions"],
                "unexpected_verdict_keys":["model","rater_alias","proposition_id"],
                "missing_verdict_keys":["model","rater_alias","proposition_id","matrix_row","publication_role","author_type","proposition_type","subject_id","hadm_id","human_gt","invalid"],
                "empty_reasons":["model","rater_alias","proposition_id","reference_id"],
            }
            for name, rows in exports.items():
                write_csv(run/(name+".csv"), rows, empty_fields.get(name) if not rows else None)
            write_json(run/"audit.json", result)
            write_json(run/"checks.json", checks.rows)
            with (run/"report.md").open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(build_report(result, exports, run.name))
            manifest["status"] = "failed_checks" if checks.failed else "completed"
            progress(f"Finished: {manifest['status']}; {len(checks.rows)} checks; {relative(run)}")
        except Exception:
            manifest["status"] = "error"
            manifest["error"] = traceback.format_exc()
            progress(manifest["error"])
        finally:
            manifest["finished_utc"] = datetime.now(timezone.utc).isoformat()
            manifest["elapsed_seconds"] = time.monotonic()-start
    manifest["output_sha256"] = {p.name:digest_file(p) for p in sorted(run.iterdir()) if p.is_file()}
    write_json(run/"manifest.json", manifest)
    return 0 if manifest["status"] == "completed" else 2
