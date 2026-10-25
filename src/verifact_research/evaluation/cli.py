"""Score a baseline or new method on an explicit, validated release cohort."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
from pathlib import Path
import sys

from verifact_research.audit.common import digest_file, new_run, read_csv, write_csv, write_json
from .core import evaluate, paired_compare
from .release import load_cohort, unique

ROOT = Path(__file__).resolve().parents[3]


def validate_cohort(cohort: list[dict], authoritative: list[dict], validity: str) -> None:
    unique(cohort, "proposition_id")
    raw = unique(authoritative, "proposition_id")
    for row in cohort:
        if row["proposition_id"] not in raw:
            raise ValueError(f"Unknown cohort ID: {row['proposition_id']}")
        source = raw[row["proposition_id"]]
        for key in ["subject_id", "hadm_id", "author_type", "proposition_type", "human_gt", "invalid"]:
            if row.get(key) != source[key]:
                raise ValueError(f"Cohort {key} disagrees with release: {row['proposition_id']}")
        if validity == "valid_only" and source["invalid"] != "False":
            raise ValueError("valid_only cohort contains invalid propositions; supply a valid-only cohort, or explicitly select --validity all")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort", type=Path, required=True, help="Explicit CSV of proposition IDs and release GT/metadata")
    parser.add_argument("--predictions", type=Path, required=True, help="CSV with unique proposition_id, verdict; exact long labels")
    parser.add_argument("--baseline-predictions", type=Path, help="Optional same-cohort baseline for paired patient bootstrap")
    parser.add_argument("--method-name", required=True)
    parser.add_argument("--validity", choices=["valid_only", "all"], default="valid_only")
    parser.add_argument("--profile", choices=["research_patient", "paper_item", "none"], default="research_patient")
    parser.add_argument("--missing", choices=["error", "available"], default="error")
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument("--release", type=Path, default=ROOT / "data/00_raw/verifact-bhc/1.1.0")
    parser.add_argument("--output-root", type=Path, default=ROOT / "outputs/002_reproduce_paper_results/evaluations")
    parser.add_argument("--run-name")
    args = parser.parse_args(argv)
    cohort = read_csv(args.cohort)[1]
    validate_cohort(cohort, load_cohort(args.release), args.validity)
    predictions = read_csv(args.predictions)[1]
    result = evaluate(cohort, predictions, profile=args.profile, missing=args.missing, iterations=args.bootstrap)
    paired = None
    if args.baseline_predictions:
        if args.missing != "error":
            raise ValueError("Paired comparison requires --missing error and an explicitly identical complete cohort")
        baseline = read_csv(args.baseline_predictions)[1]
        paired = paired_compare(cohort, baseline, predictions, iterations=args.bootstrap)
    output = args.output_root.resolve()
    if output == args.release.resolve() or args.release.resolve() in output.parents:
        raise ValueError("Evaluation output cannot be inside the release")
    run = new_run(args.output_root, args.run_name, ROOT / "data/00_raw")
    write_json(run / "metrics.json", result)
    if paired is not None:
        write_json(run / "paired_comparison.json", paired)
    write_csv(run / "cohort.csv", cohort)
    write_csv(run / "predictions.csv", [{"proposition_id": r["proposition_id"], "verdict": r["verdict"]} for r in predictions])
    files = [args.cohort, args.predictions, *([args.baseline_predictions] if args.baseline_predictions else [])]
    files += [args.release / "propositions" / name for name in ["propositions.csv.gz", "human_verdicts.csv.gz", "proposition_validity.csv.gz"]]
    files += [args.release / "reference_ehr/admissions.csv.gz"]
    write_json(run / "manifest.json", dict(
        method=args.method_name, validity_policy=args.validity, parameters={k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
        created_utc=datetime.now(timezone.utc).isoformat(), command=sys.argv,
        input_sha256={str(p): digest_file(p) for p in files},
        implementation_sha256={str(p.relative_to(ROOT)): digest_file(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        dependencies={name: importlib.metadata.version(name) for name in ["numpy", "pandas", "duckdb"]},
        output_sha256={p.name: digest_file(p) for p in sorted(run.iterdir()) if p.is_file()},
    ))
    print(f"{run}\nN={result['n']}; PA={result['percent_agreement']:.6f}; AC1={result['gwet_ac1']:.6f}; MCC={result['mcc']:.6f}")
    return 0
