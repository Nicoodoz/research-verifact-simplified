"""Freeze the new-patient comparison after development, before new clinical inputs."""
from datetime import datetime,timezone
import study009 as s

if __name__=="__main__":
    base=s.OUT/"development_001/analysis_001"
    s.check(base)
    meta=s.read_json(s.OUT/"inspection_001/confirmation_metadata.json")
    s.pilot.write_json(s.OUT/"confirmation_protocol_001.json",dict(created_utc=datetime.now(timezone.utc).isoformat(),
        patient_ids=s.patient_order()[18:24],main_methods=["A48","B48","C48"],candidate_capacity=48,
        dense_route_depth=80,bm25_route_depth=80,rrf_k=60,quota="alternate dense/BM25 unseen IDs; top24 each protected",schema="009_confirmation_v1",
        all_valid_claims=True,expected_claims=650,by_author=meta["by_author"],max_reference_body_characters=8000,max_passages=16,max_per_note=2,
        models=dict(embedding=s.EMBED_MODEL,rerank=s.RERANK_MODEL,judge=s.CHAT_MODEL),
        generation=dict(temperature=0,enable_thinking=False,max_tokens=2048),
        primary_contrast="B48 minus A48",secondary_contrasts=["C48 minus A48","C48 minus B48"],
        evaluation=dict(package="verifact_research.evaluation",profile="research_patient",iterations=1000,valid_only=True,missing_primary="error",authors_separate=True),
        judge_cache="Complete native request body within this confirmation only; repeat jobs exempt, never overwrite canonical",
        repeats=dict(count=12,rule="minimum sha256(009/confirm-repeat/v1: + proposition_id) per patient/author",role="diagnostic only"),
        review_rule=dict(label_change_cases="All B/A or C/A changes, if >24 stratify by author and improved/worsened/changed_wrong then minimum hash up to 4 per cell",
            controls="Per author up to 2 stable-correct and 2 stable-wrong with changed reference, fixed hash; key loss anchors may be added with selection reason",
            complete_outputs=True,not_medical_gold=True),
        diagnostic_interventions="After primary confirmation, freeze a small balanced add/remove/repeat set in the pre-reserved 5-CNY slot; diagnostic only, no replacement of main predictions",
        decision_basis="Development B48 lost 3 correct LLM and net5 human cases vs A48; C48 gained1 per author without loss. Small capacity/rerank/note-cap diagnostics do not justify a new primary component. Keep all three original48 comparisons, no grid or after-result replacement.",
        development_manifest_sha256=s.pilot.digest_file(base/"manifest.json"),
        implementation_sha256={p.relative_to(s.ROOT).as_posix():s.pilot.digest_file(p) for p in [s.TASK/"study009.py",s.TASK/"prepare_confirmation.py",s.TASK/"build_confirmation.py"]},
        current_spent_cny=2.79829697,confirmation_stage_caps=dict(confirm_embed=1,confirm_rerank=2,confirm_judge=26),
        total_task_cap_cny=40,new_patient_results_seen=False,reserved_test_not_used=True,remaining_development_patients=16))
    print("A48/B48/C48 frozen for all 650 valid claims in the next six development patients")
