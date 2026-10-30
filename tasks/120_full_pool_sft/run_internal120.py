"""Use the existing BF16 first-receipt evaluator for the fixed internal check."""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tasks/128_sqrt_weight_refresh'))
from extend128 import guarded_run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job', type=Path, required=True)
    guarded_run(parser.parse_args().job)
