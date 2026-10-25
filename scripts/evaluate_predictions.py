"""Common baseline/new-method evaluation entry point."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from verifact_research.evaluation.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
