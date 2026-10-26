import ast
import common100 as c
def main():
 assert c.read(c.OUT/'execution_fixture_checks.json')['status']=='PASS'
 files=[c.TASK/name for name in ['runtime100.py','gates100.py','analyze100.py','test_execution100.py']]
 for p in files:ast.parse(p.read_text(encoding='utf-8'))
 c.put(c.OUT/'runtime_analysis_freeze.json',dict(utc=c.utc(),files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in files},before_any100_response=True,selection_and_confirmation_rules_frozen=True,report_and_selfcheck_to_follow_without_rule_changes=True))
 print('Runtime and decision implementation frozen before100 answers')
if __name__=='__main__':main()
