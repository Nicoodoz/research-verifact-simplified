"""Safe offline replay to new outputs/replays child, with exact result comparison."""
import argparse
from pathlib import Path
import common027 as x
import analyze027_saved as analysis
def run(destination):
    out=Path(destination).resolve();x.c.require(out.is_relative_to(x.ROOT/'outputs/replays') and not out.exists(),'New replay child required');x.offline();analysis.run(out)
    expected=x.read(x.OUT/'analysis_002/manifest.json')['outputs'];checks={p:x.sha(out/p)==h for p,h in expected.items()};x.c.require(all(checks.values()),'Replay mismatch')
    x.put(out/'replay_check.json',dict(equal=True,files=len(checks),checks=checks,network_blocked=True,new_fits_blocked=True));print('027 replay equal:',len(checks),'files')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
