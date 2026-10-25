"""013 uses existing retrieval, evaluation, transport and dated billing."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/'outputs/013_multi_mechanism_screen'
sys.path.insert(0,str(ROOT/'tasks/011_evidence_integrity_packaging'))
import study011 as previous
pilot=previous.pilot
sf=previous.sf
native=previous.native
old=previous.previous
core=old.core
read_json=previous.read_json
seal=previous.seal
check=previous.check
RAW=previous.RAW
CHAT_MODEL=previous.CHAT_MODEL
EMBED_MODEL=previous.EMBED_MODEL
RERANK_MODEL=previous.RERANK_MODEL
BASE_HEAD='a7fca7edfde3a632f340649bbce8fc2fdeccbdbd'
NINE=ROOT/'outputs/009_retrieval_baselines/confirmation_001'
TWELVE=ROOT/'outputs/012_comparative_error_diagnosis'
# Per-stage ceilings, NOT separate task budgets. Runner also reserves against
# 40 minus every other stage's paid/unknown/in-flight cost under one task lock.
STAGE_CAPS={'unit_aux':1,'unit_judge':1,'screen_aux':9,'screen_judge':11,
            'combination':2,'confirm_aux':4,'confirm_judge':40}
METHODS=('baseline','contract','text_guard','wide_candidates','selector')

def freeze(out,dependencies=(),code_files=(),details=None):
    from datetime import datetime,timezone
    pilot.write_json(out/'manifest.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=BASE_HEAD,
        dependencies={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in dependencies},
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in code_files},
        files={p.relative_to(out).as_posix():pilot.digest_file(p) for p in out.rglob('*') if p.is_file() and p.name!='manifest.json'},details=details or {}))

def total_cost(exclude=None):
    return sum(read_json(p)['used_or_reserved_cny'] for p in (OUT/'live').glob('*/state.json') if p.parent.name!=exclude)

def judge_body(item,reference,prompts):return previous.judge_body(item,reference,prompts)
