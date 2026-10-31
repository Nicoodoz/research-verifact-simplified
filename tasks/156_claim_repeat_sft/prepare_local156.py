"""Export the original120 scientific schedule and hashes, without clinical text."""
from pathlib import Path
import json,hashlib,shutil
R=Path(__file__).resolve().parents[2];P=R/'.local_models/156_claim_repeat_sft';P.mkdir(exist_ok=True)
B=R/'.local_models/120_full_pool_sft/resume369/bundle/data';S=B/'full_pool_sft120'
rows=[json.loads(s) for s in (S/'train.jsonl').read_text(encoding='utf-8-sig').splitlines()];assert len(rows)==2945
manifest=[dict(id=r['id'],sid=str(r['sid']),GT=r['GT'],claim_sha256=hashlib.sha256(r['claim'].encode()).hexdigest(),reference_sha256=hashlib.sha256(r['reference'].encode()).hexdigest(),answer_sha256=hashlib.sha256(r['answer'].encode()).hexdigest()) for r in rows]
(P/'train_manifest.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in manifest),encoding='utf-8')
job=json.loads((B/'full_pool_sft120.json').read_text());(P/'source_job120.json').write_text(json.dumps(job,indent=2)+'\n',encoding='utf-8')
shutil.copy2(S/'plan.json',P/'original_plan.json')
print(json.dumps(dict(N=2945,patients=len({r['sid'] for r in manifest}),source107_SHA=job['source_adapter_sha256'],original_steps=369,new_reasons=False,new_GT=False)))
