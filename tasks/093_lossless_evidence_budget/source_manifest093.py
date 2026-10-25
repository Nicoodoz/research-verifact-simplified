"""Record sources read for history, provenance and independent final checks."""
import common093 as c
def main():
    names=[
      'outputs/028_traceable_claim_evidence_verification/report.md','tasks/028_traceable_claim_evidence_verification/common028.py',
      'outputs/042_coverage_aware_evidence_packing/report.md','tasks/042_coverage_aware_evidence_packing/protocol.md','tasks/042_coverage_aware_evidence_packing/common042.py','tasks/042_coverage_aware_evidence_packing/prepare042.py',
      'outputs/046_requirement_aware_retrieval_screen/report.md','tasks/046_requirement_aware_retrieval_screen/protocol.md','tasks/046_requirement_aware_retrieval_screen/prepare046.py','tasks/046_requirement_aware_retrieval_screen/build_final046.py',
      'outputs/048_end_to_end_evidence_recovery/report.md','tasks/048_end_to_end_evidence_recovery/protocol.md','tasks/048_end_to_end_evidence_recovery/common048.py','tasks/048_end_to_end_evidence_recovery/build_screen_audits048.py','tasks/048_end_to_end_evidence_recovery/build_screen_finals048.py',
      'outputs/011_evidence_integrity_packaging/README.md','tasks/011_evidence_integrity_packaging/packaging011.py',
      'outputs/047_mechanism_stratified_validation/report.md','outputs/049_evidence_decision_utilization/report.md',
      'outputs/069_final_pack_controlled_repair/report.md','outputs/069_final_pack_controlled_repair/067_correction.md',
      'outputs/081_gt_blind_evidence_selection/report.md','outputs/090_demo_constructor_repair_validation/report.md',
      'tasks/090_demo_constructor_repair_validation/common090.py','tasks/090_demo_constructor_repair_validation/api090.py','tasks/090_demo_constructor_repair_validation/analyze090.py',
      'outputs/091_integrated_evidence_decision_study/report.md','outputs/092_task_adapted_verifier/report.md',
      'outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl','outputs/031_training_expansion_confirmation/retrieval_001/candidates.jsonl','outputs/031_training_expansion_confirmation/retrieval_001/jobs.jsonl',
      'outputs/042_coverage_aware_evidence_packing/planning_001/selector_outputs.jsonl','outputs/002_reproduce_paper_results/run_003/cohort_master.csv','outputs/092_task_adapted_verifier/cohort.jsonl']
    c.put(c.OUT/'source_manifest.json',dict(utc=c.now(),HEAD='e3999daa6c7012efcadcd3c2dce641651be3592c',historical_sha256={p:c.sha(c.ROOT/p) for p in names},independent_audit=False,scope='Targeted source/history review, not full repository reaudit. No historical file modified.'))
    print('Recorded',len(names),'source hashes.')
if __name__=='__main__':main()
