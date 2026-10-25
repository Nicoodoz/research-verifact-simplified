import common095 as c
paths=[c.TASK/p for p in ['pricing095.py','pricing_verification.md','run095_v2.py','state095.py','decision_clarification.md','workflow095.py']]
c.put(c.OUT/'pricing_v2_freeze.json',dict(utc=c.now(),no_candidate_calls_yet=True,sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in paths},tariffs_cny_per_million={'busy':[3,9,.3],'idle':[1.5,4.5,.15]},idle_window='22:00-08:00 UTC+8; both transport timestamps in same idle window; otherwise busy',hard_cap_unchanged=150,normal_cap_unchanged=130))
