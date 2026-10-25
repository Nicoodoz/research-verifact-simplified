"""Independent 027 ranking, bootstrap, conflicts and source-binding audit. No fitting."""
from pathlib import Path
from collections import defaultdict
import sys,json,csv,hashlib,math,socket
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
def blocked(*a,**k):raise RuntimeError('No network or training during audit')
socket.create_connection=blocked;socket.socket.connect=blocked;socket.socket.connect_ex=blocked
LogisticRegression.fit=blocked;StandardScaler.fit=blocked
root=Path.cwd();out=Path(sys.argv[1]);base=root/'outputs/027_dual_judge_transfer_diagnosis';a=base/'analysis_002'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jl(p):return [json.loads(v) for v in p.read_text(encoding='utf-8-sig').splitlines() if v]
def csvr(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
history={}
for label in ['019_021','022','023','024','025','026']:history.update(read(root/f'reviews/artifacts/{label}_audit_20260919/audited_files_sha256.json'))
assert all(sha(root/p)==v for p,v in history.items())
items=read(a/'candidates.json');original=read(base/'analysis_001/candidates.json')
groups={g:[v for v in items if v['group']==g] for g in ['025','026']}
source025=jl(root/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl')
full={'025':[v for v in source025 if v['group']=='024_D'],'026':csvr(root/'outputs/026_frozen_sd_patient_transfer/preparation_001/cohort.csv')}
saved026={v['proposition_id']:v for v in read(root/'outputs/026_frozen_sd_patient_transfer/analysis_001/gate_inference.json')}
saved025={v['proposition_id']:v for v in csvr(root/'outputs/025_lambda_flip_risk_separability/analysis_003/candidate_oof.csv') if v['group']=='024_D' and v['method']=='SD'}
for v in items:
    expected=float(saved025[v['proposition_id']]['prob']) if v['group']=='025' else saved026[v['proposition_id']]['prob']
    assert v['SD']==expected
for g,rr in groups.items():
    p=np.array([v['SD'] for v in rr]);oldp=np.array([v['SD'] for v in original if v['group']==g])
    assert np.array_equal(np.sign(p[:,None]-p),np.sign(oldp[:,None]-oldp))
rank=csvr(a/'ranking.csv');unc=read(a/'uncertainty.json');inter=read(base/'interpretation_001/summary.json')
def pair_auc(y,s,w):
    pos=np.where(y)[0];neg=np.where(~y)[0]
    den=sum(w[pos])*sum(w[neg])
    if not den:return None
    credit=(s[pos,None]>s[None,neg]).astype(float)+.5*(s[pos,None]==s[None,neg])
    return float(np.sum(credit*w[pos,None]*w[None,neg])/den)
ranking_results={}
methods=['D_s','D_margin','Q_s','Q_margin','SD']
for g,rr in groups.items():
    subjects=sorted({v['subject_id'] for v in full[g]});assert unc[g]['cluster_patients']==subjects
    y=np.array([v['kind']=='R' for v in rr]);sid=np.array([subjects.index(v['subject_id']) for v in rr]);values={m:np.array([v[m] for v in rr]) for m in methods}
    draws={m:[] for m in methods};deltas={m:[] for m in ['Q_s','Q_margin','SD']};sd_q=[]
    for m in methods:
        row=next(v for v in rank if v['group']==g and v['method']==m and v['scope']=='all')
        assert abs(pair_auc(y,values[m],np.ones(len(rr)))-float(row['AUROC']))<1e-12
        # AP from distinct accepted-score groups; complete ties.
        old_recall=ap=0.
        for t in sorted(set(values[m]),reverse=True):
            keep=values[m]>=t;recall=sum(keep&y)/sum(y);precision=sum(keep&y)/sum(keep)
            ap+=(recall-old_recall)*precision;old_recall=recall
        assert abs(ap-float(row['AP']))<1e-12
        numerator=denominator=0.
        for s in range(len(subjects)):
            ix=sid==s;yy=y[ix];ss=values[m][ix];den=int(sum(yy))*int(sum(~yy))
            if den:numerator+=pair_auc(yy,ss,np.ones(sum(ix)))*den;denominator+=den
        assert abs(numerator/denominator-float(row['within_patient_AUROC']))<1e-12
    for seed in range(1000):
        weights=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects)),minlength=len(subjects))[sid]
        av={m:pair_auc(y,values[m],weights) for m in methods}
        for m in methods:
            if av[m] is not None:draws[m].append(av[m])
        if av['SD'] is not None:
            sd_q.append(av['SD']-av['Q_s'])
            for m in deltas:deltas[m].append(av[m]-av['D_margin'])
    for m in methods:
        assert len(draws[m])==unc[g]['AUC'][m]['valid_draws']
        np.testing.assert_allclose(np.percentile(draws[m],[2.5,97.5]),unc[g]['AUC'][m]['ci95'],atol=1e-12,rtol=0)
    for m in deltas:np.testing.assert_allclose(np.percentile(deltas[m],[2.5,97.5]),unc[g]['AUC_difference_vs_D_margin'][m],atol=1e-12,rtol=0)
    np.testing.assert_allclose(np.percentile(sd_q,[2.5,97.5]),inter['SD_vs_Q_AUC'][g]['ci95'],atol=1e-12,rtol=0)
    ranking_results[g]=dict(patients=len(subjects),candidates=len(rr),AUC_CIs_checked=5,paired_AUC_CIs_checked=4)
# Alternate integer DP: minimum risk for each exact rescue count.
conf=read(a/'conflicts.json');feature_names=read(root/'outputs/026_frozen_sd_patient_transfer/gate_freeze/gate.json')['features'];conflicts={}
for g,rr in [*groups.items(),('pooled_descriptive',items)]:
    grouped=defaultdict(list)
    for v in rr:grouped[tuple(v['features'][k] for k in feature_names)].append(v)
    counts=[(sum(v['kind']=='R' for v in vv),sum(v['kind']!='R' for v in vv)) for vv in grouped.values()]
    mixed=[(R,F) for R,F in counts if R and F];lower=sum(min(R,F) for R,F in counts)
    assert len(grouped)==conf[g]['unique_exact_groups'] and len(mixed)==len(conf[g]['mixed_groups']) and sum(R+F for R,F in mixed)==conf[g]['mixed_claims'] and lower==conf[g]['unavoidable_binary_errors']
    dp={0:0}
    for R,F in counts:
        nxt=dp.copy()
        for rescue,risk in dp.items():nxt[rescue+R]=min(nxt.get(rescue+R,math.inf),risk+F)
        dp=nxt
    for t,risk in conf[g]['oracle_min_risk_at_retention'].items():assert min(v for k,v in dp.items() if k>=math.ceil(float(t)*sum(x['kind']=='R' for x in rr)-1e-10))==risk
    raw=np.array([[v[k][label] for k in ['D_scores','Q_scores'] for label in ['Supported','Not Supported','Not Addressed']] for v in rr])
    for t in [0,5,10]:
        pp=op=cross=0
        for i in range(len(rr)):
            for j in range(i):
                if max(abs(raw[i]-raw[j]))<=t:
                    pp+=1;opposite=(rr[i]['kind']=='R')!=(rr[j]['kind']=='R');op+=opposite;cross+=opposite and rr[i]['subject_id']!=rr[j]['subject_id']
        assert conf[g]['near_summary'][str(t)]==dict(pairs=pp,opposite_pairs=op,cross_patient_opposite=cross)
    conflicts[g]=dict(exact_groups=len(grouped),mixed_groups=len(mixed),mixed_claims=sum(R+F for R,F in mixed),minimum_errors=lower)
# High-rescue ceiling reconstructed by enumerating all tied thresholds and two-point mixtures.
def envelope(cost,rescue,budget):
    cost=np.array(cost,float);rescue=np.array(rescue,float);best=max(rescue[cost<=budget],default=0.)
    lo=np.where(cost<budget)[0];hi=np.where(cost>budget)[0]
    if len(lo) and len(hi):
        vals=rescue[lo,None]+(budget-cost[lo,None])/(cost[None,hi]-cost[lo,None])*(rescue[None,hi]-rescue[lo,None]);best=max(best,float(vals.max()))
    return best
ceilings={}
for g,rr in groups.items():
    glob=[v for v in csvr(a/'global_curves.csv') if v['group']==g];cost=[float(v['risk']) for v in glob];resc=[float(v['R']) for v in glob];truth=np.array([v['kind']=='R' for v in rr]);ps=np.array([v['SD'] for v in rr]);gains=[]
    for t in sorted(set(ps),reverse=True):
        keep=ps>=t;R=sum(keep&truth);F=sum(keep&~truth)
        if R/sum(truth)>=.8:gains.append(float(R-envelope(cost,resc,F)))
    saved=inter[g]['high_rescue_SD_diagnostic_only']
    assert len(gains)==saved['points'] and abs(max(gains)-saved['mixed_gain_max'])<1e-12
    assert sum(v>=3 for v in gains)==saved['points_gain_atleast3']
    ceilings[g]=dict(states=len(gains),max_gain=max(gains),states_gain_atleast3=sum(v>=3 for v in gains))
# Every case packet is bound to original 026 text/outputs, not merely its own manifest.
source=root/'outputs/026_frozen_sd_patient_transfer';material={v['proposition_id']:v for v in jl(source/'preparation_001/inputs.jsonl')};nn={(v['proposition_id'],v['model_key']):v for v in jl(source/'analysis_001/normalized.jsonl') if v['arm']=='S'}
selected=read(a/'case_selection.json');ledger=read(base/'semantic_001/case_ledger.json');quote_count=0
assert len(ledger)==len(selected)==31
for v in ledger:
    packet=read(base/'case_material_001'/(v['case_id']+'.json'));pid=v['proposition_id']
    assert packet['claim']==material[pid]['text'] and packet['reference']==material[pid]['reference']
    assert packet['DeepSeek_output']==nn[pid,'deepseek']['output_text'] and packet['Qwen_output']==nn[pid,'qwen']['output_text']
    for q in v['anchors']:assert packet['reference'][q['start']:q['end']]==q['quote'];quote_count+=1
assert quote_count==53
for left,right in [('C06','C16'),('C14','C29')]:
    v=read(base/f'case_material_001/{left}.json');w=read(base/f'case_material_001/{right}.json')
    assert v['D_scores']==w['D_scores'] and v['Q_scores']==w['Q_scores'] and (v['features']['GT']=='Supported')!=(w['features']['GT']=='Supported')
result=dict(status='PASS',history_hashes=len(history),ranking=ranking_results,conflicts=conflicts,high_rescue_ceiling=ceilings,case_packets_bound=31,quote_offsets=quote_count,full_packet_text_read_by_auditor=['C06','C16','C14','C29'],saved_probability_order_unchanged=True,network_blocked=True,new_fits_blocked=True)
(out/'independent_summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
