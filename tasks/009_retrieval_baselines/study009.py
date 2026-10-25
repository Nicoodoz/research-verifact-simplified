"""009 paths and reuse of frozen 002/008 components; no model calls on import."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
OUT=ROOT/"outputs/009_retrieval_baselines"
PRIOR=ROOT/"outputs/008_retrieval_planning"
RAW=ROOT/"data/00_raw/verifact-bhc/1.1.0"
sys.path.insert(0,str(ROOT/"tasks/008_retrieval_planning"))
import common as prior
import planning_core as core
import build_stages as prior_stages
import services as native

pilot=prior.pilot
sf=prior.sf
read_json=prior.read_json
CHAT_MODEL=prior.CHAT_MODEL
EMBED_MODEL=prior.EMBED_MODEL
RERANK_MODEL=prior.RERANK_MODEL
BASE_HEAD="42d28c4909b901056207c6770e1be733998123cf"
STAGE_CAPS={"dev_embed":.25,"dev_rerank":.75,"dev_judge":5,"confirm_embed":1,"confirm_rerank":2,"confirm_judge":26,"diagnostics":5}
assert sum(STAGE_CAPS.values())==40


def patient_order():
    groups=read_json(ROOT/"outputs/003_error_analysis/patient_groups.json")
    return sorted(groups["groups"]["development"],key=lambda sid:pilot.digest_text(groups["seed"]+sid))


def seal(out,dependencies,code_files,details=None):
    from datetime import datetime,timezone
    pilot.write_json(out/"manifest.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),
        base_head=BASE_HEAD,dependencies={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in dependencies},
        code_sha256={p.relative_to(ROOT).as_posix():pilot.digest_file(p) for p in code_files},
        files={p.relative_to(out).as_posix():pilot.digest_file(p) for p in out.rglob("*") if p.is_file()},details=details or {}))


def check(out):
    m=read_json(out/"manifest.json")
    for name,h in m["files"].items():
        pilot.require(pilot.digest_file(out/name)==h,"Artifact changed: "+name)
    return m


def quota_candidates(dense,lexical,capacity=48):
    """Alternating unique results reserves each route's top floor(capacity/2)."""
    result=[]
    for i in range(max(len(dense),len(lexical))):
        for route in (dense,lexical):
            if i<len(route) and route[i] not in result:
                result.append(route[i])
                if len(result)==capacity:
                    return result
    return result


def candidates(rankings,method,capacity=48):
    if method=="A":
        return rankings["hybrid"][:capacity]
    dense=[pid for pid,_ in rankings["dense"]]
    if method=="B":
        return dense[:capacity]
    if method=="C":
        return quota_candidates(dense,[pid for pid,_ in rankings["bm25"]],capacity)
    raise ValueError("Unknown candidate rule")


def relaxed_plan(raw,item):
    """Normalize whitespace only for validation; keep every query and source word."""
    import copy
    obj=pilot.strict_json(raw)
    normalized=copy.deepcopy(obj)
    if isinstance(normalized,dict) and isinstance(normalized.get("source_clues"),list):
        for clue in normalized["source_clues"]:
            if isinstance(clue,dict) and isinstance(clue.get("quote"),str):
                clue["quote"]=" ".join(clue["quote"].split())
    normal_item=copy.deepcopy(item)
    normal_item["source"]["local"]=" ".join(item["source"]["local"].split())
    core.parse_plan(pilot.canonical(normalized),normal_item)
    # Validation does not rewrite saved content, add a missing field, or relax semantics.
    return obj
