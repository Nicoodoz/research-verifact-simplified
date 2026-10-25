"""Offline-only helpers for080. No credentials or networking."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).parent;OUT=ROOT/'outputs/080_final_decision_adaptation'
sys.path.insert(0,str(ROOT/'tasks/079_f4_priorg_adaptation'))
from common079 import read,lines,put,jl,sha,digest,canon,now,c53
LABELS=c53.LABELS
