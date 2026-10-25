"""Record the user's standing <=40 CNY authority; this script makes no API call."""
from datetime import datetime,timezone
import common as c

if __name__=="__main__":
    c.check_files(c.OUT/"preparation_001")
    checks=c.read_json(c.OUT/"offline_checks_001/checks.json")
    assert checks["claims"]==144 and checks["api_calls"]==0
    summary=c.read_json(c.OUT/"preparation_001/summary.json")
    assert summary["expected_total_cny"]<=40
    path=c.OUT/"authority_001.json"
    assert not path.exists()
    c.pilot.write_json(path,dict(created_utc=datetime.now(timezone.utc).isoformat(),
        authority="user_standing_approval_estimate_leq_40_CNY",user_instruction="预计总费用不超过40元时直接执行，而不是16元。继续按照上面的要求完成008。",
        task_cap_cny=40,phase_caps_cny=c.PHASE_CAPS,expected_total_cny=summary["expected_total_cny"],
        patient_ids=c.PATIENTS,claims=144,services_sha256=c.pilot.digest_file(c.TASK/"services.py"),
        executor_sha256=c.pilot.digest_file(c.TASK/"execute_phase.py"),protocol_sha256=c.pilot.digest_file(c.OUT/"execution_protocol_001.md"),
        preparation_manifest_sha256=c.pilot.digest_file(c.OUT/"preparation_001/manifest.json"),
        input_checks_sha256=c.pilot.digest_file(c.OUT/"offline_checks_001/checks.json"),
        offline_tests=dict(command="python -B -m unittest discover -s tests -v",tests=133,exit_code=0,independent_audit=False),
        price_sources_manifest_sha256=c.pilot.digest_file(c.ROOT/"docs/sources/008_retrieval_planning/manifest.json"),
        interpretation="Existing user authority recorded by execution agent, not a new per-run user reply or independent PASS"))
    print("Registered 144-claim task; expected CNY",summary["expected_total_cny"],"cap 40; no API calls")
