import common094 as c
def main():
    c.put(c.OUT/'runner_freeze.json',dict(utc=c.now(),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.TASK/'api094.py',c.TASK/'test094.py']}))
    paths=['tasks/028_traceable_claim_evidence_verification/common028.py','tasks/048_end_to_end_evidence_recovery/common048.py','tasks/039_full_ehr_attribution/common039.py','tasks/049_evidence_decision_utilization/build_screen_methods049.py','tasks/065_verification_evidence_construction/common065.py','outputs/065_verification_evidence_construction/report.md','outputs/093_lossless_evidence_budget/report.md','outputs/093_lossless_evidence_budget/case_analysis.md','outputs/093_lossless_evidence_budget/history_difference.md']
    c.put(c.OUT/'history_sources.json',dict(utc=c.now(),sources={p:c.sha(c.ROOT/p) for p in paths}))
if __name__=='__main__':main()
