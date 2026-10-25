"""Forbidden network/model sends; reconstruct all analysis to a new replay child."""
import argparse,socket
from pathlib import Path
import common028 as c
import analyze028
def blocked(*a,**k):raise RuntimeError('028 offline replay forbids API')
def run(destination):
    out=Path(destination).resolve();c.require(out.is_relative_to(c.ROOT/'outputs/replays') and not out.exists(),'New replay child required');socket.socket.connect=blocked;socket.create_connection=blocked;c.DirectClient.send=blocked;analyze028.run(out)
    expected=c.read(c.OUT/'analysis_001/manifest.json')['outputs'];checks={p:c.sha(out/p)==h for p,h in expected.items()};c.require(all(checks.values()),'Replay mismatch');c.put(out/'replay_check.json',dict(equal=True,files=len(checks),checks=checks,network_blocked=True));print('028 replay equal',len(checks))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
