import json,sys
import common093 as c
import api093
sys.path.insert(0,str(c.ROOT/'tasks/090_demo_constructor_repair_validation'))
from analyze090 import parse_arm
def main():
    job=c.read(c.PRIVATE/'preflight.json');_,success,_=api093.state();r=success[job['request_id']]
    tr=c.read(c.ROOT/r['receipt_path'])['transport'];info,labels=parse_arm(tr,None)
    c.put(c.OUT/'preflight_result.json',dict(valid=info['valid'],raw_valid=info['raw_valid'],model=json.loads(tr['body_text'])['model'],finish_reason=info['finish_reason'],usage=info['usage'],response_sha256=c.sha(c.ROOT/r['receipt_path']),synthetic=True,API_cost_or_reserved_cny=r['cost_or_reserved_cny']))
    assert info['valid'],'successful preflight core invalid: preserve and stop, no content retry'
    print('Synthetic preflight valid',info['usage'],flush=True)
if __name__=='__main__':main()
