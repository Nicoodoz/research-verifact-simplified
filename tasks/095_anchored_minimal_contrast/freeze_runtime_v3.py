import common095 as c
old=c.read(c.OUT/'pricing_v2_freeze.json');assert c.sha(c.TASK/'workflow095_pre_resume_fix.py')==old['sources'][(c.TASK/'workflow095.py').relative_to(c.ROOT).as_posix()]
paths=[c.TASK/p for p in ['pricing095.py','pricing095_v3.py','run095_v3.py','pricing_verification.md','state095.py','decision_clarification.md','workflow095.py','workflow095_pre_resume_fix.py','runtime_v3_note.md']]
c.put(c.OUT/'runtime_v3_freeze.json',dict(utc=c.now(),no_candidate_calls_yet=True,sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},prior_manifest_sha256=c.sha(c.OUT/'pricing_v2_freeze.json'),hard_cap_unchanged=150,normal_cap_unchanged=130))
