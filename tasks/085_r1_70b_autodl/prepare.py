"""Freeze only offline material; no GT-based choice and no inference."""
import subprocess
from common import *
def main():
    check_old();OUT.mkdir(parents=True,exist_ok=True)
    neutral=lines(OLD/'neutral_jobs.jsonl');assert len(neutral)==360
    jobs=[freeze_job(j) for j in neutral]
    assert len({(j['id'],j['arm']) for j in jobs})==360 and len({j['id'] for j in jobs})==180 and len({j['sid'] for j in jobs})==21
    lengths=lines(OLD/'tokenizer_lengths.jsonl');assert max(x['chat_input_tokens'] for x in lengths)+8192<=20000
    # Read and fingerprint all085A materials; do not execute their generators/selfcheck (some overwrite old paths).
    hist={}
    for folder in (ROOT/'tasks/085_r1_70b_model_swap',OLD):
        for p in folder.rglob('*'):
            if p.is_file():hist[p.relative_to(ROOT).as_posix()]=sha(p)
    old089=read(ROOT/'outputs/089_source_audited_demo_compression/delivery_manifest.json')
    for rel,d in old089['sha256'].items():assert sha(ROOT/rel)==d
    put(OUT/'historical_inventory.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),files=hist,
        old089_delivery_manifest_sha256=sha(ROOT/'outputs/089_source_audited_demo_compression/delivery_manifest.json'),gitignore_sha256=sha(ROOT/'.gitignore')))
    putl(OUT/'jobs.jsonl',jobs)
    sem=read(OLD/'prompt_semantics.json')
    a=dict(id='FICTIONAL-A-NO-PATIENT',sid='FICTIONAL',arm='B',claim='The fictional patient received a blue scarf.',reference='[1] Fictional record: the patient received a blue scarf.',instruction_semantic_content=sem['B_system_content'])
    put(OUT/'fictional_job.json',freeze_job(a))
    put(OUT/'offline_manifest.json',dict(status='AUTODL_OFFLINE_READY_AWAIT_USER_ENDPOINT',inference_calls=0,paid_API_cny=0,gpu_rental_cny=None,
        endpoint_configured=bool(os.getenv('R1_BASE_URL')),claims=180,patients=21,logical_R1_slots=360,V4_new_calls=0,GT_used=False,
        old_status='PREDEPLOY_READY_PAUSED_BY_USER',new_route='user-managed AutoDL/direct vLLM through SSH tunnel',
        longest_input_tokens=9694,max_model_len=20000,max_tokens=8192,min_context_margin=2114,
        resolved_model_revision=read(TASK/'identity_lock.json')['model']['revision'],tokenizer_revision=read(TASK/'identity_lock.json')['tokenizer']['revision'],
        remote_model_identity_verified=False,remote_gpu_verified=False,preflight_A=False,preflight_B=False,formal_authorized=False))
    # Future real server manifest is produced remotely; this is explicitly not a valid service certificate.
    put(OUT/'server_manifest_requirements.json',dict(status='REQUIREMENTS_ONLY_NOT_OBSERVED',required=['model.repo','model.resolved_revision','model.files hashes','model.config/quantization','tokenizer.repo/revision/files/chat_template_sha256','versions.vllm/torch/transformers','gpu','server_command','environment','actual live process observation'],credentials_allowed=False))
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in TASK.rglob('*') if p.is_file() and p.name not in ('selfcheck.py','test_offline.py')}
    sources.update(hist)
    put(OUT/'offline_freeze.json',dict(status='FROZEN_OFFLINE_NO_ENDPOINT',created_utc=now(),sources=sources,
        files={p.name:sha(p) for p in OUT.iterdir() if p.is_file()}))
    print(canonical(read(OUT/'offline_manifest.json')))
if __name__=='__main__':main()
