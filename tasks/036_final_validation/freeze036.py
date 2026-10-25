"""Bind all development-only parameters and whole-task forecast before paid requests."""
import sys,hashlib,shutil,json,math
import numpy as np
import common036 as c
import api036 as a
def main():
    out=c.OUT/'final_freeze_001';assert not out.exists() and not (c.OUT/'attempts').exists()
    d=c.OUT/'development_001';assert (d/'manifest.json').exists()
    meta=c.csvread(c.OUT/'planning_001/claim_metadata.csv');sids=sorted(set(r['subject_id'] for r in meta),key=lambda s:hashlib.sha256(('036/repeat/v1:'+s).encode()).hexdigest())
    norms=c.lines(c.ROOT/'outputs/026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl')
    means={}
    for role,arm in [('baseline','B'),('score','S')]:
        us=[r['usage'] for r in norms if r['model_key']=='deepseek' and r['arm']==arm]
        means[role]=float(np.mean([(u['prompt_tokens']*3+u['completion_tokens']*9)/1e6 for u in us]))
    us=[r['usage'] for r in norms if r['model_key']=='qwen'];means['peer']=float(np.mean([(u['prompt_tokens']*3+u['completion_tokens']*12)/1e6 for u in us]))
    bge=[]
    for p in (c.ROOT/'outputs/031_training_expansion_confirmation/attempts').glob('*/request.json'):
        rq=c.read(p);j=rq['job']
        if j['kind']!='rerank' or not (p.parent/'receipt.json').exists():continue
        tr=c.read(p.parent/'receipt.json')['transport']
        if tr['http_status']==200:bge.append(a.native.cost(j,tr)[0])
    assert bge and all(np.isfinite(list(means.values())))
    embed=sum(a.bound(j) for j in c.lines(c.OUT/'materials_001/embedding_jobs.jsonl'))
    retrieval=embed+2*float(np.mean(bge))*len(meta) # x2 historic mean rerank, byte bound for embedding
    options=[]
    for k in (6,4,0):
        repeat=sids[:k];nr=sum(r['subject_id'] in repeat for r in meta);n=len(meta)+nr
        expected=retrieval+n*(means['baseline']+means['score'])+math.ceil(n*.25)*means['peer']
        protected=expected*1.2+3
        options.append(dict(repeat_patients=k,repeat_claims=nr,expected_cny=expected,plus20pct_plus3_cny=protected))
        if protected<=c.CAP:break
    c.require(protected<=c.CAP,'Forecast above150; no paid calls allowed')
    out.mkdir(parents=True)
    sources={'gate_A.json':c.ROOT/'outputs/033_gate_training_subset/recommendation_001/gate_A_all40.json','models035.json':c.ROOT/'outputs/035_lambda_boundary_calibration/run_002/full_development_models.json','standard_models022.json':d/'standard_full_development_models.json'}
    for name,path in sources.items():shutil.copyfile(path,out/name)
    gate=c.read(out/'gate_A.json');assert len(gate['final_fit']['features'])==12 and gate['threshold']==0.608679899116368
    config=dict(created_utc=c.now(),lambda_fixed=2,score_floor=1e-6,tie_order=['Not Supported','Not Addressed','Supported'],patient_ids=sorted(sids),repeat_patients=repeat,repeat_seed='036/repeat/v1:',repeat_independent_peer=True,methods=['O','B','Score_verdict','U0','U2','U2_T','Gate_A','Std_T','Std_G','Std_M','Std_V','Joint_NLL','Task_T','Robust_T','MCC_T','U4'],primary_pairs=[['U2','U0'],['U2','B'],['U2','O'],['Gate_A','U2'],['U2_T','U2']],bootstrap=1000,bootstrap_seeds=list(range(1000)),missing_peer='fallback_U0',missing_score='explicit missing; paired complete-case with total-N sensitivity',reserved_GT_read=False,cap_cny=150,account_skip=['account_1','account_2'],account_skip_reason='account_1 disabled; account_2 documented031401 and user authorized next enabled account; user036 authorizes routine engineering under current routing',models=a.api.MODELS,role_bodies={role:a.body('SCHEMA_ONLY_SYNTHETIC_CLAIM','SCHEMA_ONLY_SYNTHETIC_REFERENCE',role) for role in ('baseline','score','peer')})
    c.put(out/'config.json',config)
    c.put(out/'budget.json',dict(created_utc=c.now(),total_claims=len(meta),repeat_choice=options[-1],considered_options=options,historical_mean_role_cny=means,rerank_031_mean_cny=float(np.mean(bge)),BGE_forecast_cny=retrieval,embedding_byte_bound_cny=embed,planning_candidate_rate=.25,cap_cny=c.CAP,price_basis='Peak no-cache; actual charges estimates not invoiced; individual byte/token reservations enforced',prices_CNY_per_million={'deepseek':[3,9],'qwen':[3,12],'Pro_BGE':.07},official_sources=['https://help.aliyun.com/zh/model-studio/deepseek-v4-flash','https://help.aliyun.com/zh/model-studio/model-pricing','https://siliconflow.cn/pricing'],price_checked_this_turn=True,new_requests_before_freeze=0))
    c.put(out/'environment.json',c.base.environment())
    c.put(out/'manifest.json',dict(created_utc=c.now(),source_hashes={str(p.relative_to(c.ROOT)):c.sha(p) for p in sources.values()},files={p.name:c.sha(p) for p in out.iterdir() if p.is_file()},protocol_sha256=c.sha(c.TASK/'protocol.md'),development_manifest_sha256=c.sha(d/'manifest.json')))
    print(json.dumps(c.read(out/'budget.json'),ensure_ascii=False),flush=True)
if __name__=='__main__':main()
