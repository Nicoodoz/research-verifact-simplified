"""Canonical027: use026 stored probability bytes after recomputation check.

Initial analysis_001 used equivalent JSON-parameter reconstruction; retain it.
This entry reads saved probabilities exactly, without changing any model.
"""
import argparse
from pathlib import Path
import analyze027 as base
import common027 as x
original_load=base.load
original_sources=base.sources
def load():
    groups,items,gate=original_load();saved={r['proposition_id']:r for r in x.read(x.ROOT/'outputs/026_frozen_sd_patient_transfer/analysis_001/gate_inference.json')}
    for r in items:
        if r['group']=='026':r['SD']=saved[r['proposition_id']]['prob']
    return groups,items,gate
def sources():return original_sources()+[Path(__file__)]
def run(out):
    base.load=load;base.sources=sources;base.run(out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();out=Path(a.output).resolve() if a.output else x.OUT/'analysis_002';x.c.require(out==x.OUT/'analysis_002' or out.is_relative_to(x.ROOT/'outputs/replays'),'Unsafe output');run(out)
