"""Read-only integrity replay; does not load credentials, import live runner, or send APIs."""
from collections import Counter
import common024 as c
def run():
    jobs=c.verify_inputs()
    cp=c.ROOT/'outputs/020_lambda2_patient_validation/new10/preparation_002/cohort.csv'
    c.require(c.file_hash(cp)==c.file_hash(c.OUT/'preparation_001/cohort.csv'),'Cohort differs from020')
    ins={r['proposition_id']:r for r in c.lines(c.ROOT/'outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl')}
    c.require(len(jobs)==3516 and len({j['request_id'] for j in jobs})==3516,'Expected complete unique factorial')
    counts=Counter()
    for j in jobs:
        x=ins[j['proposition_id']];b=c.old.body(x['text'],x['reference'],j['arm']=='S');b['model']=c.MODELS[j['model_key']]
        c.require(b==j['body'],'020 claim/reference or019 prompt/settings mismatch')
        counts[(j['proposition_id'],j['model_key'],j['arm'])]+=1
    c.require(len(counts)==3516 and all(n==1 for n in counts.values()),'Duplicate logical request')
    attempts,terminal=c.load_attempts(jobs)
    c.require(sum(a['charge_cny'] for a in attempts)<=80,'Over budget')
    for p in c.OUT.glob('checkpoint_*/manifest.json'):
        for rel,h in c.read(p)['sha256'].items():c.require(c.file_hash(c.ROOT/rel)==h,'Checkpoint changed: '+rel)
    print(c.canonical(dict(input_requests_verified=len(jobs),terminal=len(terminal),valid=sum(p['status']=='success' for p in terminal.values()),occupied_cny=sum(a['charge_cny'] for a in attempts),new_api_calls=0)))
if __name__=='__main__':run()
