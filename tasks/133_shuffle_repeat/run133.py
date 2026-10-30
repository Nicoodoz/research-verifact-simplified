"""Launch the unchanged120 training implementation only after a concrete decision."""
from pathlib import Path
import argparse,json,subprocess,sys

R=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    if sys.platform!='linux':raise RuntimeError('GPU launch belongs to the authorized Linux instance')
    decision=R/'data/shuffle_repeat/decision.json'
    if not decision.exists() or json.loads(decision.read_text()).get('execute') is not True:
        raise RuntimeError('Await the completed132 and training-fit decision; CPU preparation is not launch authorization')
    command=[sys.executable,'-B','-u',str(R/'tasks/120_full_pool_sft/run120.py'),
        '--job',str(R/'data/shuffle_repeat/job.json')]
    if args.resume:command.append('--resume')
    return subprocess.call(command,cwd=R)
if __name__=='__main__':raise SystemExit(main())
