"""Offline-only replay to a NEW outputs/replays child, never historical paths."""
import argparse,socket
from pathlib import Path
import common026 as c
import analyze026

def blocked(*args,**kwargs):raise RuntimeError('026 offline replay: network disabled')

def run(destination):
    out=Path(destination).resolve()
    c.require(out.is_relative_to(c.ROOT/'outputs/replays') and not out.exists(),'Use a new outputs/replays child')
    socket.socket.connect=blocked;socket.create_connection=blocked;c.DirectClient.send=blocked
    analyze026.run(out)
    expected=c.read(c.OUT/'analysis_001/manifest.json')['outputs_sha256']
    checks={name:c.sha(out/name)==digest for name,digest in expected.items()}
    c.require(all(checks.values()),'Replay mismatch: '+str(checks))
    c.put(out/'replay_check.json',dict(all_equal=True,network_disabled=True,checks=checks))
    print(c.canonical(dict(replay_equal=True,files=len(checks))))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');run(p.parse_args().destination)
