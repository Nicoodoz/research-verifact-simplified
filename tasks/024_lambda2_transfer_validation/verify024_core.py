"""Safe read-only full-input/accounting/parser verification; no credentials or APIs."""
from collections import Counter
import core024 as c
def run():
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs)
    for folder in ('checkpoint_001','checkpoint_002'):
        for rel,h in c.read(c.OUT/folder/'manifest.json')['sha256'].items():c.require(c.file_hash(c.ROOT/rel)==h,'Historical checkpoint changed: '+rel)
    for name in ('amendment_001/execution_manifest_002.json','amendment_002/evaluation_code_manifest.json'):
        for rel,h in c.read(c.OUT/name)['sha256'].items():c.require(c.file_hash(c.ROOT/rel)==h,'Frozen code changed: '+rel)
    cp=c.ROOT/'outputs/020_lambda2_patient_validation/new10/preparation_002/cohort.csv'
    c.require(c.file_hash(cp)==c.file_hash(c.OUT/'preparation_001/cohort.csv'),'020 cohort changed')
    ins={r['proposition_id']:r for r in c.lines(c.ROOT/'outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl')}
    c.require(len(jobs)==len({j['request_id'] for j in jobs})==3516,'Logical ID mismatch')
    for j in jobs:
        r=ins[j['proposition_id']];body=c.old.body(r['text'],r['reference'],j['arm']=='S');body['model']=c.MODELS[j['model_key']]
        c.require(body==j['body'],'Frozen claim/reference/prompt/settings changed')
    cnt=Counter(a['request_id'] for a in attempts);c.require(all(n<=3 for n in cnt.values()),'Unregistered retry count')
    byid={j['request_id']:j for j in jobs};unchanged=0
    for a in attempts:
        d=c.OUT/a['attempt_dir'];req=c.read(d/'request.json')
        c.require(req['prior_task_used_or_reserved_cny']+req['reservation_cny']<=80+1e-10,'Send exceeded reservation cap')
        if (d/'receipt.json').exists():
            tr=c.read(d/'receipt.json')['transport'];j=byid[a['request_id']]
            old=c.old.prior.parse(tr,j['arm']=='S');new=c.parse(tr,j['arm']=='S')
            if old['status']=='success':
                c.require(new['status'] in c.VALID and old['verdict']==new['verdict'] and old['scores']==new['scores'],'Previously valid core changed');unchanged+=1
    c.require(sum(a['charge_cny'] for a in attempts)<=80,'Budget exceeded')
    if (c.OUT/'analysis_001/manifest.json').exists():
        m=c.read(c.OUT/'analysis_001/manifest.json')
        for rel,h in m['sha256'].items():c.require(c.file_hash(c.ROOT/rel)==h,'Analysis dependency changed: '+rel)
        for name,h in m['outputs_sha256'].items():c.require(c.file_hash(c.OUT/'analysis_001'/name)==h,'Analysis output changed: '+name)
    print(c.canonical(dict(frozen_requests_verified=len(jobs),attempts=len(attempts),http200=len(terminal),status=dict(Counter(v['status'] for v in terminal.values())),original_valid_core_unchanged=unchanged,occupied_cny=sum(a['charge_cny'] for a in attempts),new_api_calls=0)))
if __name__=='__main__':run()
