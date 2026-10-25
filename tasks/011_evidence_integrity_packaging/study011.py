"""011 reuses frozen retrieval/Judge/evaluation; imports never call a service."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/011_evidence_integrity_packaging'
sys.path.insert(0,str(ROOT/'tasks/010_verifact_baseline_alignment'))
import alignment_common as old
previous=old.previous
previous_io=old.previous_io
pilot=old.pilot
native=old.native
sf=old.sf
read_json=old.read_json
CHAT_MODEL=old.CHAT_MODEL
EMBED_MODEL=old.EMBED_MODEL
RERANK_MODEL=old.RERANK_MODEL
RAW=old.RAW
PRIOR=old.PRIOR
BASE_HEAD='1d6e4e0d9d2756f1be8a50305d2605e212b43344'
METHODS=('A','B','C')
STAGE_CAPS={'pilot':5,'main':35}
assert sum(STAGE_CAPS.values())==40

def seal(out,dependencies,code_files,details=None):
    from datetime import datetime,timezone
    pilot.write_json(out/'manifest.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=BASE_HEAD,
        dependencies={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in dependencies},
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in code_files},
        files={p.relative_to(out).as_posix():pilot.digest_file(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'},details=details or {}))

def check(out):
    m=read_json(out/'manifest.json')
    for name,digest in m['files'].items():
        pilot.require(pilot.digest_file(out/name)==digest,'Frozen output changed: '+name)
    for name,digest in {**m.get('dependencies',{}),**m.get('code_sha256',{})}.items():
        pilot.require(pilot.digest_file(ROOT/name)==digest,'Frozen input/computation changed: '+name)
    return m

def judge_body(item,reference,prompts):
    return previous.prior_stages.judge_body(item,reference,prompts)
