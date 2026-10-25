"""Read-only receipt decoding, exact-body cache and original structured normalization."""
from datetime import datetime
import json
import alignment_common as s


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


normalize=s.previous_io.normalize
