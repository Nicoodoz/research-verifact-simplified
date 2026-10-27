"""Finish only still-missing native requests after the diagnosed128 runner exits."""
import time
import common103 as c
import runtime103 as rt
from run_api103 import guarded
def main():
 while (c.PRIVATE/'run.lock').exists():time.sleep(2)
 freeze=c.read(c.OUT/'api_execution_freeze.json')
 for rel,h in freeze['files'].items():assert c.sha(c.ROOT/rel)==h
 jobs=[j for j in c.lines(c.PRIVATE/'jobs_selected.jsonl') if j['mode']=='native']
 rt.process=guarded;rt.run(jobs,workers=16)
 assert all(j['request_id'] in rt.completed() for j in jobs)
 print('ALL_NATIVE_COMPLETE')
if __name__=='__main__':main()
