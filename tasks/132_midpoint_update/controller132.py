"""Explicitly invoked on the authorized existing Linux instance."""
from pathlib import Path
import argparse,json,subprocess,sys,time

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser();p.add_argument('--scope',choices=('screen160','old500','internal687'),required=True);a=p.parse_args()
    if sys.platform!='linux':raise RuntimeError('Only launch on the authorized GPU host')
    job_path=ROOT/'data/midpoint'/a.scope/'job.json';job=json.loads(job_path.read_text())
    folder=Path(job['final_adapter'])
    if not (folder/'composition.json').exists():
        subprocess.run([sys.executable,'-B',str(ROOT/'tasks/132_midpoint_update/compose132.py'),
            '--anchor','/root/autodl-tmp/verifact109/bundle/source107/checkpoint_a',
            '--candidate','/root/autodl-tmp/verifact120_resume369/results/full_pool_sft/train/checkpoint_b',
            '--out',str(folder)],check=True)
    comp=json.loads((folder/'composition.json').read_text())
    if comp['adapter_sha256']!=job['adapter_sha256']:raise ValueError('Remote and CPU construction differ')
    result=subprocess.run([sys.executable,'-B','-u',str(ROOT/'tasks/128_sqrt_weight_refresh/extend128.py'),
        'run','--job',str(job_path)],cwd=ROOT)
    (ROOT/('controller_'+a.scope+'.json')).write_text(json.dumps(dict(exit_code=result.returncode,epoch=time.time(),no_shutdown=True)))
    return result.returncode


if __name__=='__main__':raise SystemExit(main())
