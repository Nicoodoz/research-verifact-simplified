"""050 shared scoring utilities."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/050_repeated_score_aggregation"
SCREEN_CAP=20.0
TOTAL_CAP=50.0
MODEL="deepseek-v4-flash-0731"
PRICE=(3,9)
VALID=("valid","valid_with_format_anomaly")
sys.path.insert(0,str(ROOT/"tasks/048_end_to_end_evidence_recovery"))
import common048 as c48
canonical=c48.canonical;require=c48.require;score_body=c48.score_body;parse_score=c48.parse_score
ulabel=c48.ulabel;stable=c48.stable;now=c48.now;sha=c48.sha;read=c48.read;lines=c48.lines
put=c48.put;jsonl=c48.jsonl;csvwrite=c48.csvwrite;digest=c48.digest

def bound(job):
    b=job["body"];ip,op=PRICE
    return ((len(canonical(b).encode())+2000)*ip+b.get("max_tokens",1500)*op)/1e6
def charge(job,tr):
    try:
        u=json.loads(tr["body_text"])["usage"];ip,op=PRICE
        return (int(u["prompt_tokens"])*ip+int(u["completion_tokens"])*op)/1e6
    except Exception:return bound(job)
