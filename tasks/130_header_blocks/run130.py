"""Explicit inference entry for the fixed grouped-reference candidate."""
from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/128_sqrt_weight_refresh'))
from extend128 import guarded_run,common
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--job',type=Path,required=True)
    a=p.parse_args();job=common.read(a.job)
    if job['task']!=130 or job['candidate']!='header_blocks' or not job['no_training']:
        raise ValueError('Wrong fixed inference-only task')
    guarded_run(a.job)
