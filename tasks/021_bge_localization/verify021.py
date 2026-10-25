"""Offline closure verification for task 021."""
from pathlib import Path
import csv, json, math, subprocess
import numpy as np
import common021 as c

EXPECTED_SOURCE={
    'outputs/020_lambda2_patient_validation/new10/preparation_002/manifest.json':'b6f8cf42f2dd1e980306b4c190f7e8a0a7d8f85c6c28b2458ac5ceba1fcf9ed2',
    'outputs/020_lambda2_patient_validation/new10/preparation_002/embedding_catalog.json':'3e3c4601d93ed204bdc2e07994897d640aa0deff8e09411f17ccd243907e31ad',
    'outputs/020_lambda2_patient_validation/new10/candidates_001/manifest.json':'5f5c2c9a7c3b94ae58fe93dac525753bba0e799d81058a04f41f8c83ff879d25',
    'outputs/020_lambda2_patient_validation/new10/candidates_001/candidates.jsonl':'0bd0dcdc6e84558eb6646ea79a99d9f32ccb89813006422482e9012626223943',
    'outputs/020_lambda2_patient_validation/new10/candidates_001/jobs.jsonl':'2332d5862625c50179b5d5e896edbdaf73a5af0ce532a951829468a0fbd2ebfb',
    'outputs/020_lambda2_patient_validation/new10/candidates_001/embedding_ids.json':'53ca35b01379c74fcbf612cc26cb9ce2e12a675373ad4fb3314ab73b13e3aa0b',
    'outputs/020_lambda2_patient_validation/new10/candidates_001/vectors.npy':'f8e2d022e4be5ebfc620cd25a0d31fc83e543ab02e554e5077208e43a89d2da5',
    'outputs/020_lambda2_patient_validation/new10/base_preparation_001/inputs.jsonl':'eeef805259c8fbbb3eed6731448c6d83a03711182eb34b4b767f969cda87d1bc',
}
def req(x,msg):
    if not x: raise ValueError(msg)

def main():
    reg=c.read(c.OUT/'registration_001.json')
    req(c.sha256(c.OUT/'protocol_001.md')==reg['protocol_sha256'],'protocol changed')
    for name,h in EXPECTED_SOURCE.items():
        req(c.sha256(c.ROOT/name)==h,'020 source changed: '+name)
    req(c.sha256(c.EMBED_MODEL/'pytorch_model.bin')==c.EMBED_LFS_SHA,'embedding weight hash')
    req(c.sha256(c.RERANK_MODEL/'model.safetensors')==c.RERANK_LFS_SHA,'reranker weight hash')

    ids=c.read(c.OUT/'local_embedding_ids.json')
    v16=np.load(c.OUT/'local_vectors_fp16.npy',allow_pickle=False)
    v32=np.load(c.OUT/'local_vectors_fp32.npy',allow_pickle=False)
    req(len(ids)==2057 and len(set(ids))==2057,'embedding ids')
    req(v16.shape==v32.shape==(2057,1024),'embedding shape')
    req(np.isfinite(v16).all() and np.isfinite(v32).all(),'embedding finite')

    can=c.jsonlines(c.OUT/'local_candidates_fp32.jsonl')
    rr=c.jsonlines(c.OUT/'local_rerank_scores_fp32emb_fp16rr_b32.jsonl')
    req(len(can)==len(rr)==879,'879 rows')
    cp={x['proposition_id'] for x in can}; rp={x['proposition_id'] for x in rr}
    req(len(cp)==len(rp)==879 and cp==rp,'claim identity')
    req(all(len(x['scores'])>0 and all(math.isfinite(float(v)) for v in x['scores'].values()) for x in rr),'rerank finite')

    with (c.OUT/'claim_comparison.csv').open(encoding='utf-8-sig',newline='') as f:
        comp=list(csv.DictReader(f))
    req(len(comp)==879 and {x['proposition_id'] for x in comp}==cp,'comparison rows')

    summary=c.read(c.OUT/'comparison_summary.json')
    req(summary['claims']==879,'summary claims')
    req(summary['new_paid_api_calls']==0 and summary['reserved_test_used'] is False and summary['gt_or_judge_performance_read'] is False,'scope flags')
    req(summary['frozen_equivalent_pass'] is False,'strict equivalence result changed')
    req(summary['end_to_end']['reference_exact']==565,'reference exact recount')
    req(summary['reranker']['isolated_reference_exact']==594,'reranker isolation recount')

    gitignore_clean=subprocess.run(['git','diff','--quiet','HEAD','--','.gitignore'],cwd=c.ROOT).returncode==0
    ignored=subprocess.run(['git','check-ignore','-q','.local_models/021/bge-m3/pytorch_model.bin'],cwd=c.ROOT).returncode==0
    req(gitignore_clean,'project .gitignore modified')
    req(ignored,'local model weights not ignored')

    result={
        'status':'pass',
        'offline_only':True,
        'source_020_hashes_unchanged':True,
        'embedding_vectors':2057,
        'rerank_claims':879,
        'rerank_pairs':sum(len(x['scores']) for x in rr),
        'comparison_claims':879,
        'model_weight_hashes_match_hf_lfs':True,
        'project_gitignore_unchanged':True,
        'local_model_weights_ignored_by_local_git_info_exclude':True,
        'new_paid_api_calls':0,
        'reserved_test_used':False,
        'gt_or_judge_performance_read':False,
        'strict_frozen_equivalence_pass':False,
        'api_c48_local_reranker_reference_exact':594,
        'full_local_reference_exact':565,
    }
    c.save(c.OUT/'verification_001.json',result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
if __name__=='__main__':
    main()
