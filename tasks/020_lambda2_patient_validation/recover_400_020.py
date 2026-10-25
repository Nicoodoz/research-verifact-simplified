import time
from pathlib import Path
import common020 as c
from atomic020 import load,save
O=c.OUT; lp=O/'live_ledger.json'
state=load(lp); phase=state['phases']['new10_judge']
rid='020:new10:r1:29093318242fb4bb60c993795bc9feed7c28f5c6e77d56f2db6bb36dd6693d05'
p=phase['jobs'][rid]
c.require(p['status']=='failed_configuration' and p['attempts']==1,'Unexpected recovery source state')
c.require(p['receipts'] and p['receipts'][-1]['file'].endswith('receipt_001092_01.json'),'Unexpected receipt binding')
p['status']='retry';p['transient']=max(1,int(p.get('transient',0)));p['retry_after']=0
state.pop('pause_reason',None);state['consecutive_transport_errors']=0
state.setdefault('provider_json_decode_retries',[]).append(dict(created_utc=c.now(),request_id=rid,attempt=1,reclassified_from='configuration_http_400',reason='provider_code_20015_JSON_decode_error_after_local_body_validation'))
state['_checkpoint_seq']=int(state.get('_checkpoint_seq',0))+1
save(lp,state)
print(c.canonical(dict(request_id=rid,status=p['status'],attempts=p['attempts'],transient=p['transient'],used_or_reserved_cny=state['used_or_reserved_cny'],pause_reason=state.get('pause_reason'))))
