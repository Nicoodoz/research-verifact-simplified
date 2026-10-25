"""No API calls: record the user's explicit 009 total 40-CNY authority."""
from datetime import datetime,timezone
import study009 as s

if __name__=="__main__":
    s.check(s.OUT/"development_001/preparation")
    paths=[s.TASK/"study009.py",s.ROOT/"tasks/008_retrieval_planning/planning_core.py",
        s.ROOT/"tasks/008_retrieval_planning/services.py",s.ROOT/"tasks/004_event_alignment_pilot/siliconflow.py",
        s.ROOT/"src/verifact_research/evaluation/core.py",s.ROOT/"src/verifact_research/evaluation/metrics.py"]
    s.pilot.write_json(s.OUT/"authority_001.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),base_head=s.BASE_HEAD,
        authority="User explicitly authorized task 009 unattended within total CNY 40, including development/confirmation/diagnostics/retries across all accounts",
        expected_total_cny=28.0,task_cap_cny=40,stage_caps_cny=s.STAGE_CAPS,
        native_stage_sha256=s.pilot.digest_file(s.TASK/"native_stage.py"),protocol_sha256=s.pilot.digest_file(s.OUT/"execution_protocol_001.md"),
        immutable_source_sha256={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in paths},
        development_preparation_sha256=s.pilot.digest_file(s.OUT/"development_001/preparation/manifest.json"),
        confirmation_metadata_sha256=s.pilot.digest_file(s.OUT/"inspection_001/confirmation_metadata.json"),
        preliminary_offline_tests=dict(total=140,exit_code=0,additional_baseline_tests=7),invoice_verified=False,
        no_new_clinical_test_patients=True,no_paid_preflight=True))
    print("009 authority recorded; total cap CNY 40, no API calls")
