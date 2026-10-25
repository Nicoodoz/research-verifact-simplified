import common094 as c
def main():
    paths=['tasks/015_disagreement_adjudication/common015.py','tasks/016_disagreement_triggered_review_validation/common016.py','outputs/016_disagreement_triggered_review_validation/report.md','tasks/087_f4_evidence_intervention/common087.py','tasks/090_demo_constructor_repair_validation/analyze090.py','tasks/092_task_adapted_verifier/analyze092.py','tasks/092_task_adapted_verifier/metrics092.py']
    paths += [p.relative_to(c.ROOT).as_posix() for p in (c.ROOT/'src/verifact_research/evaluation').glob('*.py')]
    c.put(c.OUT/'analysis_sources.json',dict(utc=c.now(),sources={p:c.sha(c.ROOT/p) for p in paths},note='Unmodified historical parser, frozen PriorG and official evaluator; not a new fit.'))
if __name__=='__main__':main()
