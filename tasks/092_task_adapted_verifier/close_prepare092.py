"""Preserve local pause history and bind transferred cloud work before final analysis."""
import json,subprocess,platform
import common092 as c
def main():
    old='a17e4bff9a405f7c2473cd28cfb810c025f5e9ca'
    changes=subprocess.check_output(['git','diff','--name-only',old,'--','outputs/092_task_adapted_verifier'],text=True).splitlines()
    archive=c.OUT/'local_pause_archive';archive.mkdir(exist_ok=True)
    for name in changes+['outputs/092_task_adapted_verifier/report.md']:
        raw=subprocess.check_output(['git','show',old+':'+name]);dest=archive/name.split('outputs/092_task_adapted_verifier/')[1];dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():assert dest.read_bytes()==raw
        else:dest.write_bytes(raw)
    oldbags=[json.loads(s) for s in subprocess.check_output(['git','show',old+':outputs/092_task_adapted_verifier/bags.jsonl']).splitlines()]
    assert oldbags==c.lines(c.OUT/'bags.jsonl')
    locked=c.read(c.OUT/'training_freeze_v3.json')
    assert all(c.sha(c.TASK/k)==v for k,v in locked['code'].items())
    check=c.read(c.PRIVATE/'transfer_check.json')
    assert all(v['weight_sha_match'] and v['strict_load'] and v['finite'] and v['resume_epochs']==5 for v in check['models'])
    assert all(check['base_checks'].values()) and check['input_sha_match']
    cloud=dict(status='TRAINING_COMPLETE_USER_TRANSFERRED',utc=c.now(),local_pause_commit=old,training_code_and_config_match_freeze_v3=True,
        bags_semantically_identical_to_local_pretraining=True,inputs_sha256=c.sha(c.PRIVATE/'inputs.jsonl'),
        cloud_environment_file='092_autodl_environment.txt',cloud_environment_sha256=c.sha(c.OUT/'092_autodl_environment.txt'),
        actual_cloud=dict(OS='Linux',python='3.12.3',GPU='RTX 4090 24GB',torch='2.8.0+cu128',CUDA_runtime='12.8',transformers='4.56.1'),
        reused_freeze_environment_note='training_freeze_v3 environment describes local RTX3060 preparation, not AutoDL; actual cloud environment is the supplied text file.',
        models=check['models'],backbone_hash_checks=check['base_checks'],cloud_activation_cache_transferred=False,
        local_cache_note='Old RTX3060 cache remains; equal input/window mapping and backbone do not imply byte-identical RTX4090 activations. Closure diagnostics use explicitly identified local cache, with numerical bridge measured.',
        rental_cost_cny=None,API_calls=0,API_cost_cny=0,remote_command_log_available=False,
        remaining='one registered fusion, deployment benchmark, analysis, report, manuscript, executor checks; no further model search')
    c.put(c.OUT/'cloud_training_manifest.json',cloud)
    pairs=c.read(c.OUT/'paired.json');p=pairs['common_finetuned_vs_B']
    c.put(c.OUT/'fusion_decision.json',dict(run_fusion=True,utc=c.now(),reason='Independent error complementarity: 66 B errors corrected, including 49 S and 16 NA; standalone is not superior. Execute only preregistered scalar fusion and matched bias-only control.',basis=dict(rescue=p['rescue'],harm=p['harm'],by_GT=p['rescue_by_GT']),GT_used_for_conditional_research_decision=True,independent_confirmation=False,variants=1,protocol_sha256=c.sha(c.TASK/'optional_fusion_protocol.md'),no_new_API=True))
    print('Cloud provenance verified; pause archive preserved; one fusion authorized by frozen conditional rule.')
if __name__=='__main__':main()
