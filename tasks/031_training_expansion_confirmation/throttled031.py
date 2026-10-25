"""Operational pacing only: preserve all requests, roles, output and budgets."""
import threading,time
import common031 as c
import api031 as a
import resume031
def run(stage):
    original=a.native.HttpClient.send;lock=threading.Lock();clock=[0.];spacing=[2.]
    def paced(self,account,job):
        with lock:
            delay=max(0.,clock[0]-time.monotonic())
            if delay:time.sleep(delay)
            clock[0]=time.monotonic()+spacing[0]
        result=original(self,account,job)
        if result.get('http_status')==429:
            with lock:spacing[0]=min(8.,spacing[0]*2);clock[0]=max(clock[0],time.monotonic()+30)
        return result
    path=c.OUT/'pacing_amendment_001.json'
    if not path.exists():c.put(path,dict(created_utc=c.now(),reason='14 real SF rerank429 TPM limit reached;672 valid already preserved',minimum_start_spacing_seconds=2,rate_error_spacing_double_max8=True,rate_error_cooldown_seconds=30,unchanged=['model','body','prompt','candidate','evidence','GT','lambda','feature','learning'],requires_no_new_user_research_choice=True,code_sha256=c.sha(c.TASK/'throttled031.py')))
    else:c.require(c.sha(c.TASK/'throttled031.py')==c.read(path)['code_sha256'],'Pacing code changed')
    a.native.HttpClient.send=paced;resume031.main(stage)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('embedding','rerank'));run(p.parse_args().stage)
