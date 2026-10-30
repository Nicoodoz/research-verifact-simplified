"""Explicit GPU entry for the prepared input diagnostic; no training."""
from pathlib import Path
import argparse
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/128_sqrt_weight_refresh'))
import extend128 as engine


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--job',type=Path,required=True)
    a=p.parse_args()
    job=engine.common.read(a.job)
    if job.get('task')!=129 or job.get('candidate')!='reference_blank' or job.get('N')!=160:
        raise ValueError('Only the frozen160 empty-reference diagnostic is allowed')
    if job.get('no_training') is not True or job.get('no_shutdown') is not True:
        raise ValueError('Invalid execution boundary')
    rows=engine.common.rows(engine.resolve(job['inputs_path']))
    if any(row.get('reference')!='' for row in rows):
        raise ValueError('129 must use the declared empty-reference intervention')
    engine.guarded_run(a.job)


if __name__=='__main__':main()
