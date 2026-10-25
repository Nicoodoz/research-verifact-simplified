"""Read-only offline verification; no original085A generator is executed."""
import ast,subprocess
from collections import Counter
from common import *
def main():
    check_old();checks=0
    def ok(v,msg):
        nonlocal checks
        assert v,msg;checks+=1
    hist=read(OUT/'historical_inventory.json')
    for rel,d in hist['files'].items():ok(sha(ROOT/rel)==d,rel)
    ok(sha(ROOT/'.gitignore')==hist['gitignore_sha256'],'gitignore')
    ok(sha(ROOT/'outputs/089_source_audited_demo_compression/delivery_manifest.json')==hist['old089_delivery_manifest_sha256'],'089 manifest')
    for rel,d in read(ROOT/'outputs/089_source_audited_demo_compression/delivery_manifest.json')['sha256'].items():ok(sha(ROOT/rel)==d,rel)
    f=read(OUT/'offline_freeze.json')
    for rel,d in f['sources'].items():ok(sha(ROOT/rel)==d,rel)
    for name,d in f['files'].items():ok(sha(OUT/name)==d,name)
    jobs=lines(OUT/'jobs.jsonl');old=lines(OLD/'neutral_jobs.jsonl');mapping={(x['id'],x['arm']):x for x in old}
    ok(len(jobs)==360 and len({x['id'] for x in jobs})==180 and len({x['sid'] for x in jobs})==21,'cohort')
    ok(Counter(x['arm'] for x in jobs)=={'B':180,'F4':180},'arms')
    for j in jobs:
        src=mapping[j['id'],j['arm']];ok(j==freeze_job(src),'unaltered semantic body')
        ok(json.loads(j['body']['messages'][1]['content'])==dict(proposition=src['claim'],reference=src['reference']),'target/GT')
        ok(set(j['body'])=={'model','messages','temperature','top_p','max_tokens','stream'},'no new decoder/provider fields')
    lengths=lines(OLD/'tokenizer_lengths.jsonl');ok(max(x['chat_input_tokens'] for x in lengths)+8192==17886,'context margin')
    lock=read(TASK/'identity_lock.json');ok(lock['model']['repo']==MODEL and lock['tokenizer']['repo']==TOKENIZER,'exact identity target')
    ok(lock['tokenizer']['revision']==read(OLD/'tokenizer_source.json')['revision'],'tokenizer frozen')
    ok(all(x.get('sha256') for n,x in lock['model']['files'].items() if n.endswith('.safetensors')),'all weight content hashes available')
    for p in TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));ok(True,'python syntax:'+p.name)
    ok(not (OUT/'attempts').exists(),'no real inference at offline handoff')
    ok(not (OUT/'service_identity.json').exists(),'no simulated real identity')
    ok(not (OUT/'preflight').exists(),'no fabricated preflight')
    ok(not (OUT/'formal_runs').exists(),'no formal authorization/use')
    ok(not any(p.suffix in ('.safetensors','.bin','.pt','.pth') for folder in (TASK,OUT) for p in folder.rglob('*') if p.is_file()),'no downloaded weights')
    result=dict(status='PASS',checks=checks,synthetic_tests=11,network_calls=0,inference_calls=0,independent_audit=False,
        remote_vllm_execution_tested=False,created_utc=now(),freeze_sha256=sha(OUT/'offline_freeze.json'))
    if (OUT/'selfcheck.json').exists():
        previous=read(OUT/'selfcheck.json');ok(previous['freeze_sha256']==result['freeze_sha256'],'selfcheck replay freeze');print(canonical(dict(status='PASS',checks=checks,network_calls=0)))
    else:put(OUT/'selfcheck.json',result);print(canonical(result))
if __name__=='__main__':main()
