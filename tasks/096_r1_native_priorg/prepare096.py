"""Exact051 training reconstruction and proportional sample, strictly offline."""
import sys,copy,math,collections,csv
import common096 as c
from calibration096 import fit_g,decode
sys.path.insert(0,str(c.ROOT/'tasks/051_thinking_mode_validation'))
import run051,common051 as c51

def strata_sample(pool,n,seed):
    groups=collections.defaultdict(list)
    for r in pool:groups[(r['author'],r['GT'])].append(r)
    exact={k:n*len(v)/len(pool) for k,v in groups.items()};quota={k:math.floor(x) for k,x in exact.items()}
    for k in sorted(groups,key=lambda k:(-(exact[k]-quota[k]),k))[:n-sum(quota.values())]:quota[k]+=1
    out=[]
    for k,bag in sorted(groups.items()):
        for r in sorted(bag,key=lambda r:(c.key(seed,r['id']),r['id']))[:quota[k]]:
            out.append(dict(r,stratum=list(k),inclusion_probability=quota[k]/len(bag),inclusion_weight=len(bag)/quota[k]))
    assert len(out)==n
    return sorted(out,key=lambda r:c.key(seed+'order/',r['id'])),{'|'.join(k):dict(population=len(groups[k]),sample=quota[k]) for k in sorted(groups)}

def distribution(rr):
    return dict(N=len(rr),patients=len({r['sid'] for r in rr}),GT=dict(collections.Counter(r['GT'] for r in rr)),author=dict(collections.Counter(r['author'] for r in rr)),reference_source=dict(collections.Counter(r['C48_source'] for r in rr)))

def main():
    c.OUT.mkdir(parents=True,exist_ok=True);c.PRIVATE.mkdir(parents=True,exist_ok=True)
    source=c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl';base=c.lines(source);assert len(base)==9065
    cal=c.read(c.ROOT/'outputs/052_first_tier_validation/calibration_models.json');freeze53=c.read(c.ROOT/'outputs/053_thinking_prior_validation/freeze.json');train=cal['training']['T-S'];ids=train['ids'];patients=set(train['patients']);assert len(ids)==143 and len(patients)==16
    _,terminal=run051.state();cases={r['id']:r for name in ['screen_cases.jsonl','confirmation_cases_frozen.jsonl'] for r in c.lines(c51.OUT/name)}
    ts={x['job']['id']:x for x in terminal.values() if x['job'].get('condition')=='T-S'}
    # Historical job schema may label the condition differently; match the
    # frozen request-ID prefix, never GT or result quality.
    if not ts:ts={x['job']['id']:x for rid,x in terminal.items() if rid.startswith(('051_T_S_','051_conf_T_S_'))}
    oldjobs=c.lines(c.ROOT/'.local_models/085_valdemardi_private/jobs.jsonl');template=next(j['body'] for j in oldjobs if j['arm']=='B');assert template['model']==c.MODEL
    assert not set(template)&{'enable_thinking','reasoning_effort'}
    calrows=[];jobs=[];calmeta=[]
    def job(pid,sid,stage,payload):
        b=copy.deepcopy(template);b['messages'][1]['content']=c.encoded(payload).decode();bh=c.digest(b)
        return dict(id=pid,sid=sid,stage=stage,body=b,body_sha256=bh,request_id=c.key('096/r1/'+stage+'/'+pid+'/',bh)[:32])
    for pid in ids:
        x=ts[pid];p=x['parsed'];assert p['status'] in c51.VALID and p['scores'] is not None
        q=cases[pid];oldbody=x['job']['body'];payload=c.read_payload(oldbody) if hasattr(c,'read_payload') else __import__('json').loads(oldbody['messages'][1]['content'])
        assert set(payload)=={'proposition','reference'} and oldbody['messages'][0]['content']==template['messages'][0]['content']
        r=dict(id=pid,sid=str(q['sid']),GT=q['GT'],scores=p['scores']);calrows.append(r);j=job(pid,r['sid'],'calibration',payload);jobs.append(j)
        calmeta.append(dict(id=pid,sid=r['sid'],GT=r['GT'],source051_request_id=x['job']['request_id'],claim_sha256=c.key('',payload['proposition']),reference_sha256=c.key('',payload['reference']),request_id=j['request_id'],body_sha256=j['body_sha256']))
    assert dict(collections.Counter(r['GT'] for r in calrows))==train['GT_counts']
    reproduced,independent=fit_g(calrows);theta=cal['models']['T-S']['G']['theta'][0];assert abs(reproduced['theta'][0]-theta)<1e-5
    ref=freeze53['reference_prior_counts'];counts=train['GT_counts'];assert ref=={'Supported':1108,'Not Supported':100,'Not Addressed':170}
    changed=sum(decode(r['scores'],theta,ref,counts)!=decode(r['scores'],reproduced['theta'][0],ref,counts) for r in calrows);assert changed==0
    c.putl(c.PRIVATE/'calibration_supervision.jsonl',calrows);c.putl(c.OUT/'calibration_manifest.jsonl',calmeta)
    c.put(c.OUT/'calibration_recipe.json',dict(old_theta=theta,reproduced_model=reproduced,independent_objective_check=independent,label_differences_on143=changed,reference_counts=ref,calibration_counts=counts,patients=sorted(patients),N=143,score_floor=1e-6,L2=.01,bounds=[-6,6],tie_break=['Not Supported','Not Addressed','Supported'],recipe_sources={p:c.sha(c.ROOT/p) for p in ['tasks/052_first_tier_validation/fit_calibration052.py','outputs/052_first_tier_validation/calibration_models.json','tasks/053_thinking_prior_validation/common053.py','outputs/053_thinking_prior_validation/freeze.json']},future_invalid_rule='R1/core valid intersection; counts recalculated; V4 refit on identical IDs; old V4 frozen kept separately'))
    excluded085={j['id'] for j in oldjobs};assert len(excluded085)==180
    ledger=[];eligible=[]
    for r in base:
        reason='calibration_patient' if r['sid'] in patients else '085_prior_ID' if r['id'] in excluded085 else None
        a={k:r[k] for k in ['id','sid','GT','author','C48_source','B_core_valid','B_raw_valid']};a['exclusion_reason']=reason;a['eligible']=reason is None;ledger.append(a)
        if reason is None:eligible.append(a)
    main800,q800=strata_sample(eligible,800,'096/main/v1/');main600,q600=strata_sample(eligible,600,'096/main/v1/');assert {r['id'] for r in main600}<={r['id'] for r in main800}
    used={r['id'] for r in main800};pressure=[]
    for label in ['Not Supported','Not Addressed']:
        avail=[r for r in eligible if r['id'] not in used and r['GT']==label];assert len(avail)>=100
        pressure+=sorted(avail,key=lambda r:c.key('096/stress/v1/',r['id']))[:100]
    stress100=[]
    for label in ['Not Supported','Not Addressed']:stress100+=sorted([r for r in pressure if r['GT']==label],key=lambda r:c.key('096/stress/v1/',r['id']))[:50]
    meta={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')};baseidx={r['id']:r for r in base}
    for stage,rr in [('main',main800),('stress',pressure)]:
        for r in rr:
            inp=meta[r['id']];b=baseidx[r['id']];assert c.key('',inp['text'])==b['claim_sha256'] and c.key('',inp['reference'])==b['reference_sha256']
            jobs.append(job(r['id'],r['sid'],stage,dict(proposition=inp['text'],reference=inp['reference'])))
    variants={'main800_stress200':dict(main_ids=[r['id'] for r in main800],stress_ids=[r['id'] for r in pressure]),'main600_stress100':dict(main_ids=[r['id'] for r in main600],stress_ids=[r['id'] for r in stress100]),'main800_only':dict(main_ids=[r['id'] for r in main800],stress_ids=[]),'main600_only':dict(main_ids=[r['id'] for r in main600],stress_ids=[])}
    c.putl(c.OUT/'candidate_ledger.jsonl',ledger);c.putl(c.OUT/'main_panel.jsonl',main800);c.putl(c.OUT/'stress_panel.jsonl',pressure);c.put(c.OUT/'panel_variants.json',variants)
    c.put(c.OUT/'sampling_summary.json',dict(universe=distribution(ledger),eligible=distribution(eligible),main=distribution(main800),stress=distribution(pressure),calibration_patients=sorted(patients),excluded_085_ids=180,exclusion_counts=dict(collections.Counter(r['exclusion_reason'] for r in ledger)),quotas_main800=q800,quotas_main600=q600,selection='author x GT proportional largest remainder; SHA256 within stratum, no patient quota or correctness selection',weights='N_h/n_h; near self-weighting, standardized estimates retained',core_filter_used=False,noncore_selected=sum(not r['B_core_valid'] for r in main800),GT_in_inference=False))
    c.putl(c.PRIVATE/'evaluation_labels.jsonl',[dict(id=r['id'],sid=r['sid'],GT=r['GT'],author=r['author']) for r in main800+pressure])
    c.putl(c.PRIVATE/'V4_Original_comparator_cache.jsonl',[baseidx[r['id']] for r in main800+pressure])
    bridge=sorted(main800,key=lambda r:c.key('096/v4bridge/v1/',r['id']))[:48];optional=sorted(main800,key=lambda r:c.key('096/originalstyle/v1/',r['id']))[:120]
    c.putl(c.OUT/'optional_subsets.jsonl',[dict(id=r['id'],subset=tag) for tag,rr in [('V4_batch_bridge48',bridge),('original_style_feasibility120',optional)] for r in rr])
    c.putl(c.PRIVATE/'jobs.jsonl',jobs);c.putl(c.OUT/'request_manifest.jsonl',[{k:j[k] for k in ['id','sid','stage','request_id','body_sha256']} for j in jobs]);c.put(c.PRIVATE/'template.json',template)
    fictional=job('fictional-preflight','synthetic','technical',dict(proposition='The synthetic patient has a temperature of 37 C.',reference='1. Synthetic record: Temperature measured at 37 C.'))
    c.put(c.PRIVATE/'fictional_job.json',fictional)
    sourcefiles=['docs/01_codex_execution_prompt.md','outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl','outputs/085_r1_70b_valdemardi/profile.json','outputs/052_first_tier_validation/calibration_models.json','outputs/053_thinking_prior_validation/freeze.json','tasks/085_r1_70b_model_swap/parse_r1.py']
    c.put(c.OUT/'data_freeze.json',dict(status='OFFLINE_REQUESTS_FROZEN_NOT_AUTHORIZED_TO_SEND',start_HEAD='28daf95e9b12270d8089246176023c66c4cf298e',model=c.MODEL,requests=len(jobs),calibration=143,main=800,stress=200,source_sha256={p:c.sha(c.ROOT/p) for p in sourcefiles},jobs_sha256=c.sha(c.PRIVATE/'jobs.jsonl'),manifest_sha256=c.sha(c.OUT/'request_manifest.jsonl'),network_calls=0,paid_API_calls=0,old096_status='User stopped and removed old construction task; not restored',ready_message_required=True))
    print('OFFLINE_PREPARED',len(jobs),'eligible',len(eligible),'patients',len({r['sid'] for r in eligible}),'theta',reproduced['theta'])
if __name__=='__main__':
    import socket
    from unittest.mock import patch
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Offline preparation forbids network')):main()
