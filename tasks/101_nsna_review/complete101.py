"""Close101 only after full execution, numerical selfcheck and public privacy scan."""
import common101 as c
from publication101 import scan
def main():
 check=c.read(c.OUT/'selfcheck.json');assert check['status']=='PASS';assert c.read(c.OUT/'analysis_complete.json')['full_confirmation'];scan()
 record=dict(utc=c.utc(),status='COMPLETE',scientific_status='失败停止',default_changed=False,new_API_or_reserved_cny=c.read(c.OUT/'cost_ledger.json')['used_or_reserved_cny'],hard_cap_cny=30,confirmation_natural_N=600,confirmation_pressure_N=100,review_triggered=282,independent_repeat_N=24,independent_audit=False,Git_publication_authorized=True,report_sha256=c.sha(c.OUT/'report.md'),case_analysis_sha256=c.sha(c.OUT/'case_analysis.md'),selfcheck_sha256=c.sha(c.OUT/'selfcheck.json'))
 c.put(c.OUT/'complete.json',record);print(c.canonical(record))
if __name__=='__main__':main()
