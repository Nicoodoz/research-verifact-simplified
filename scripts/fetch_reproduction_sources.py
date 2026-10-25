"""Fetch pinned public author-code references; never execute downloaded code."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

COMMIT = "f115d36cb65fa2073fce0a10df56bb37f4cbcd50"
FILES = [
    "LICENSE",
    "packages/irr_metrics/src/irr_metrics/interrater.py",
    "packages/irr_metrics/src/irr_metrics/classification_metrics.py",
    "packages/irr_metrics/src/irr_metrics/metric_bunch.py",
    "packages/irr_metrics/src/irr_metrics/constants.py",
    "scripts/analysis_interrater/1_compute_interrater_agreement.py",
    "scripts/analysis_interrater/2_interrater_agreement_tables.py",
    "scripts/analysis_interrater/README.md",
    "scripts/analysis_verifact/README.md",
    "scripts/analysis_verifact/release_data.py",
    "scripts/analysis_verifact/2_compute_verifact_metrics.py",
    "scripts/analysis_verifact/3_sensitivity_analysis_plots.py",
    "scripts/analysis_verifact/4_agreement_mcc_plots.py",
    "scripts/analysis_verifact/5_best_model_classification_metrics.py",
    "scripts/analysis_verifact/6_metric_result_tables.py",
    "scripts/analysis_verifact/9a_confusion_matrices_llama_vs_R1.py",
    "scripts/analysis_verifact/11_compute_verifact_metrics_stratified.py",
    "scripts/analysis_verifact/12_analyze_verifact_agreement_stratified.py",
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "docs/sources/verifact_upstream_f115d36cb65f"
    target.mkdir(exist_ok=False)
    records = []
    for name in FILES:
        url = f"https://raw.githubusercontent.com/philipchung/verifact/{COMMIT}/{name}"
        request = urllib.request.Request(url, headers={"User-Agent": "Research-VeriFact/002"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content = response.read()
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(content)
        records.append({"path": name, "url": url, "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest()})
        print(name, flush=True)
    with (target / "source_manifest.json").open("x", encoding="utf-8", newline="\n") as handle:
        json.dump({"repository": "https://github.com/philipchung/verifact", "commit": COMMIT,
                   "retrieved_utc": datetime.now(timezone.utc).isoformat(), "files": records},
                  handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


if __name__ == "__main__":
    main()
