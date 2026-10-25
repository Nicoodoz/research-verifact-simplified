"""018 offline sources and002 evaluation; imports never send requests."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];TASK=Path(__file__).resolve().parent;OUT=ROOT/'outputs/018_verifact_gap_attribution'
sys.path.insert(0,str(ROOT/'tasks/017_verification_supervised_evidence_utility'))
import common017 as prior
from common017 import read,write_json,write_csv,write_lines,jsonlines,csvrows,canonical,fingerprint,file_hash,require,now,evaluate,paired_compare,LABELS
sys.path.insert(0,str(ROOT/'tasks/012_comparative_error_diagnosis'))
import study012 as twelve
from inspect_references import blocks
TEN=ROOT/'outputs/010_verifact_baseline_alignment'
SIXTEEN=ROOT/'outputs/016_disagreement_triggered_review_validation'
RAW=prior.old.RAW
BUCKETS=('O_only','C_only','both_wrong','both_correct')

def bucket(o,c,g):return 'both_correct' if o==g and c==g else 'O_only' if o==g else 'C_only' if c==g else 'both_wrong'
def seal(folder,deps=(),code=()):
    write_json(folder/'manifest.json',dict(created_utc=now(),files={p.relative_to(ROOT).as_posix():file_hash(p) for p in folder.rglob('*') if p.is_file()},
        dependencies={p.relative_to(ROOT).as_posix():file_hash(p) for p in deps},code_sha256={p.relative_to(ROOT).as_posix():file_hash(p) for p in code}))
def check(folder):
    m=read(folder/'manifest.json')
    for key in ('files','dependencies','code_sha256'):prior.old.check_hashes(m[key])
    return m
