"""Read-only receipt decoding, exact-body cache and original structured normalization."""
from datetime import datetime
import json
import study009 as s


def stage(phase):
    base=s.OUT/"live"/phase
    manifest=s.read_json(base/"manifest.json")
    state=s.read_json(base/"state.json")
    assert state["run_id"]==s.pilot.fingerprint(manifest)
    values,attempts={},[]
    for job in manifest["jobs"]:
        rid=job["request_id"]
        p=state["jobs"][rid]
        received=[]
        for ptr in p["receipts"]:
            path=base/ptr["file"]
            assert s.pilot.digest_file(path)==ptr["sha256"]
            receipt=s.read_json(path)
            assert receipt["run_id"]==state["run_id"] and receipt["job_sha256"]==s.pilot.fingerprint(job) and receipt["request_id"]==rid
            charge,basis=s.native.cost(job,receipt["transport"])
            assert abs(charge-ptr["charge_cny"])<1e-10 and basis==ptr["charge_basis"]
            attempts.append(dict(phase=phase,request_id=rid,attempt=receipt["attempt"],http_status=receipt["transport"]["http_status"],
                charge_cny=charge,charge_basis=basis,receipt=path.relative_to(s.ROOT).as_posix(),sha256=ptr["sha256"],account=receipt["account"]))
            if receipt["transport"]["http_status"]==200:
                received.append((receipt,path))
        for missing in p.get("unreceipted_attempts",[]):
            attempts.append(dict(phase=phase,request_id=rid,attempt=missing["attempt"],http_status=0,
                charge_cny=missing["reserved_cny"],charge_basis="unreceipted_unknown_reservation",receipt="",sha256="",account=p.get("account","")))
        assert len(received)<=1,"Saved successful answer regenerated"
        value=dict(job=job,status=p["status"],native=None,receipt=None)
        if received:
            receipt,path=received[0]
            try:
                native=s.pilot.strict_json(receipt["transport"]["body_text"])
            except (ValueError,TypeError):
                native=None
            value.update(native=native,receipt=receipt,receipt_path=path.relative_to(s.ROOT).as_posix())
        values[rid]=value
    assert abs(sum(x["charge_cny"] for x in attempts)-state["used_or_reserved_cny"])<1e-8
    return values,attempts


def old_judge_cache():
    values,_=s.prior_stages.phase_data("judge")
    assignments=s.pilot.read_csv(s.PRIOR/"judge_preparation_001/assignments.csv")[1]
    eligible={r["request_id"] for r in assignments}
    state=s.read_json(s.PRIOR/"live/judge/state.json")
    result={}
    for rid in eligible:
        v=values[rid]
        ptr=state["jobs"][rid]["receipts"][-1]
        key=s.pilot.fingerprint(v["job"]["body"])
        assert key not in result
        result[key]=dict(request_id=rid,receipt_path=(s.PRIOR/"live/judge"/ptr["file"]).relative_to(s.ROOT).as_posix(),
            receipt_sha256=ptr["sha256"],body=v["job"]["body"],native=v["native"],receipt=v["receipt"],source="008_exact_body_canonical")
    return result


def normalize(job,receipt,pid):
    if receipt is None:
        return dict(request_id=job["request_id"],proposition_id=pid,status="failed",verdict=None,structural_errors=["No received response"],adherence_errors=[])
    tr=receipt["transport"]
    try:
        native=s.pilot.strict_json(tr["body_text"])
    except (ValueError,TypeError):
        native=None
    data=s.pilot.strict_json(job["body"]["messages"][1]["content"])
    elapsed=(datetime.fromisoformat(tr["ended_utc"])-datetime.fromisoformat(tr["started_utc"])).total_seconds() if tr.get("ended_utc") and tr.get("started_utc") else 0
    return s.sf.normalize_result(dict(request_id=job["request_id"],proposition_id=pid,arm="structured",request_sha256=s.pilot.fingerprint(job["body"])),
        dict(reference=data["reference"]),dict(http_status=tr["http_status"],response_json=native,elapsed_seconds=elapsed,ended_utc=tr.get("ended_utc")),
        dict(judge=dict(model_id=s.CHAT_MODEL),generation=dict(max_output_tokens=2048),budget=dict(visible_explanation_word_limit=200)))


def rerank_scores(value):
    assert value["status"]=="received" and isinstance(value["native"],dict),"Missing rerank response"
    job,native=value["job"],value["native"]
    if native.get("model") is not None:
        assert native["model"]==s.RERANK_MODEL
    rows=native["results"]
    assert sorted(x["index"] for x in rows)==list(range(len(job["passage_ids"]))),"Incomplete rerank indices"
    import math
    scores={job["passage_ids"][x["index"]]:float(x["relevance_score"]) for x in rows}
    assert all(math.isfinite(score) for score in scores.values())
    return scores
