"""010 paths and frozen 002/009 reuse; importing performs no model calls."""
from pathlib import Path
from datetime import datetime,timezone
import sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/010_verifact_baseline_alignment'
PRIOR=ROOT/'outputs/009_retrieval_baselines/confirmation_001'
RAW=ROOT/'data/00_raw/verifact-bhc/1.1.0'
BASE_HEAD='b336a6fd01755e2e6cbf1da55656826e43b51182'
sys.path.insert(0,str(ROOT/'tasks/009_retrieval_baselines'))
import study009 as previous
import io009 as previous_io
pilot=previous.pilot
sf=previous.sf
native=previous.native
read_json=previous.read_json
CHAT_MODEL=previous.CHAT_MODEL
EMBED_MODEL=previous.EMBED_MODEL
RERANK_MODEL=previous.RERANK_MODEL
STAGE_CAPS={'judge':40}
METHODS=('verifact_reference','c48_reference')

def seal(out,dependencies,code_files,details=None):
    pilot.write_json(out/'manifest.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=BASE_HEAD,
        dependencies={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in dependencies},
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in code_files},
        files={p.relative_to(out).as_posix():pilot.digest_file(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'},details=details or {}))

def check(out,dependencies=True):
    m=read_json(out/'manifest.json')
    for name,digest in m['files'].items():
        pilot.require(pilot.digest_file(out/name)==digest,'Frozen artifact changed: '+name)
    if dependencies:
        for name,digest in {**m.get('dependencies',{}),**m.get('code_sha256',{})}.items():
            pilot.require(pilot.digest_file(ROOT/name)==digest,'Frozen computation/input changed: '+name)
    return m

def judge_body(item,reference,prompts):
    return previous.prior_stages.judge_body(item,reference,prompts)

def evaluate_separately(cohort,predictions):
    return {author:pilot.evaluate([r for r in cohort if r['author_type']==author],
        [p for p in predictions if p['proposition_id'] in {r['proposition_id'] for r in cohort if r['author_type']==author}],iterations=1000)
        for author in ('llm','human')}
