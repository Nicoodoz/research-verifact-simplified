"""Read-only 090 decision-path diagnosis; no refitting or threshold search."""
from common091 import *
from itertools import combinations

def pair_summary(z,base,cand,method):
    def isfs(x,a):return x['GT']!=LABELS[0] and x['labels'][a][method]==LABELS[0]
    ids={k:[] for k in ('rescue','harm','false_S_added','false_S_removed')}
    for x in z:
        bc=x['labels'][base][method]==x['GT'];cc=x['labels'][cand][method]==x['GT']
        if not bc and cc:ids['rescue'].append(x['id'])
        if bc and not cc:ids['harm'].append(x['id'])
        if not isfs(x,base) and isfs(x,cand):ids['false_S_added'].append(x['id'])
        if isfs(x,base) and not isfs(x,cand):ids['false_S_removed'].append(x['id'])
    return dict(n=len(z),**{k:len(v) for k,v in ids.items()},net=len(ids['rescue'])-len(ids['harm']),ids=ids)

def auc(z):
    sids=sorted({x['sid'] for x in z});ix=np.array([sids.index(x['sid']) for x in z]);truth=np.array([LABELS.index(x['GT']) for x in z]);w=np.array([np.bincount(np.random.RandomState(i).randint(0,len(sids),len(sids)),minlength=len(sids)) for i in range(1000)])
    scores={a:np.array([logs(x['arms'][a]['scores']) for x in z]) for a in ARMS};out={}
    for c,d in combinations(range(3),2):
        pos=np.where(truth==c)[0];neg=np.where(truth==d)[0];v={};draw={}
        if not len(pos) or not len(neg):out[f'{LABELS[c]} / {LABELS[d]}']=dict(defined=False);continue
        for arm,l in scores.items():
            q=np.round(l[:,c]-l[:,d],12);delta=q[pos,None]-q[neg][None,:];win=(delta>0).astype(float)+.5*(delta==0)
            matrix=np.zeros((len(sids),len(sids)));np.add.at(matrix,(np.broadcast_to(ix[pos,None],win.shape).ravel(),np.broadcast_to(ix[neg][None,:],win.shape).ravel()),win.ravel())
            den=(w@np.bincount(ix[pos],minlength=len(sids)))*(w@np.bincount(ix[neg],minlength=len(sids)))
            ds=np.divide(np.einsum('bi,ij,bj->b',w,matrix,w),den,out=np.full(1000,np.nan),where=den>0);draw[arm]=ds
            check=roc_auc_score(np.r_[np.ones(len(pos)),np.zeros(len(neg))],np.r_[q[pos],q[neg]])
            assert abs(check-win.mean())<1e-12
            same=ix[pos,None]==ix[neg][None,:]
            v[arm]=dict(AUC=float(win.mean()),within_patient_AUC=float(win[same].mean()) if same.any() else None,within_patient_pairs=int(same.sum()))
        delta=draw['P90']-draw['F4'];valid=delta[np.isfinite(delta)]
        out[f'{LABELS[c]} / {LABELS[d]}']=dict(defined=True,n_positive=len(pos),n_negative=len(neg),arms=v,P_minus_F=v['P90']['AUC']-v['F4']['AUC'],CI95=np.quantile(valid,[.025,.975]).tolist(),valid_bootstrap_draws=len(valid))
    return out

def main():
    src=ROOT/'outputs/090_demo_constructor_repair_validation';rows=lines(src/'predictions_public.jsonl');old=read(src/'analysis.json');attempts=lines(src/'attempt_ledger.jsonl');at={x['request_id']:x for x in attempts};frozen=[src/'predictions_public.jsonl',src/'analysis.json',src/'attempt_ledger.jsonl',ROOT/'tasks/087_f4_evidence_intervention/common087.py',ROOT/'outputs/078_component_ablation/postprocessing_frozen.json',TASK/'protocol.md',TASK/'common091.py',Path(__file__)]
    snapshots=bind(frozen);detail=[];summaries={}
    for x in rows:
        for arm in ARMS:
            v=x['arms'][arm];s=v['scores']
            if v['valid']:
                assert decision(s,0)==x['labels'][arm]['U0'];assert decision(s,2)==x['labels'][arm]['U2'];assert priorg(s)==x['labels'][arm]['PriorG']
                x['labels'][arm]['prior_only']=prior_only(s)
            else:x['labels'][arm]['prior_only']=x['labels'][arm]['PriorG']
    for panel in ('natural','pressure'):
        full=[x for x in rows if x['panel']==panel];z=[x for x in full if all(x['arms'][a]['valid'] for a in ARMS)];y=[x['GT'] for x in z]
        met={a:{m:metrics(y,[x['labels'][a][m] for x in z]) for m in METHODS} for a in ARMS}
        original=metrics(y,[x['labels']['Original']['PriorG'] for x in z])
        for a in ARMS:
            for m in ('raw','U0','U2','PriorG'):
                oldm=old['panels'][panel]['common_core_metrics'][m][a]
                for key in ('correct','false_S','MCC','PA'):assert abs(met[a][m][key]-oldm[key])<1e-12
        full_summary={a:{m:metrics([x['GT'] for x in full],[x['labels'][a][m] for x in full]) for m in METHODS} for a in ARMS}
        transitions=[];joint=[];post={};patterns=[]
        for a in ARMS:
            for before,after in (('raw','U0'),('U0','U2'),('U0','prior_only'),('prior_only','PriorG'),('raw','PriorG')):
                counts=Counter((x['GT'],x['labels'][a][before],x['labels'][a][after]) for x in z)
                transitions.extend(dict(arm=a,before=before,after=after,GT=k[0],old=k[1],new=k[2],n=n) for k,n in sorted(counts.items()))
                post[a+'/'+before+'->'+after]=dict(rescue=sum(x['labels'][a][before]!=x['GT'] and x['labels'][a][after]==x['GT'] for x in z),harm=sum(x['labels'][a][before]==x['GT'] and x['labels'][a][after]!=x['GT'] for x in z),changed=sum(x['labels'][a][before]!=x['labels'][a][after] for x in z))
            counts=Counter(tuple(x['arms'][a]['scores'][k] for k in LABELS) for x in z)
            for score,n in counts.most_common():
                sub=[x for x in z if tuple(x['arms'][a]['scores'][k] for k in LABELS)==score]
                if any(x['labels'][a]['raw']!=x['labels'][a]['PriorG'] for x in sub):patterns.append(dict(arm=a,scores=score,n=n,GT=dict(Counter(x['GT'] for x in sub)),raw=dict(Counter(x['labels'][a]['raw'] for x in sub)),final=dict(Counter(x['labels'][a]['PriorG'] for x in sub)),patients=sorted({x['sid'] for x in sub})))
        c=Counter()
        for x in z:
            b=x['labels']['F4'];p=x['labels']['P90'];bits=tuple(int(pred==x['GT']) for pred in (b['raw'],p['raw'],b['PriorG'],p['PriorG']));c[(x['GT'],)+bits]+=1
            rd=bits[1]-bits[0];fd=bits[3]-bits[2]
            kind='raw_gain_retained' if rd==1 and fd==1 else 'raw_gain_both_final_correct' if rd==1 and bits[2:]==(1,1) else 'raw_gain_both_final_wrong' if rd==1 and bits[2:]==(0,0) else 'raw_gain_reversed' if rd==1 else 'raw_harm_erased' if rd==-1 and fd==0 else 'raw_harm_retained' if rd==-1 and fd==-1 else 'raw_harm_reversed' if rd==-1 else 'final_only_rescue' if fd==1 else 'final_only_harm' if fd==-1 else 'no_net_change'
            rec=dict(id=x['id'],sid=x['sid'],panel=panel,GT=x['GT'],kind=kind,raw_delta=rd,final_delta=fd,labels={a:x['labels'][a] for a in ARMS},scores={a:x['arms'][a]['scores'] for a in ARMS},margins={a:dict(raw_S=float(logs(x['arms'][a]['scores'])[0]-max(logs(x['arms'][a]['scores'])[1:])),final_S=float((logs(x['arms'][a]['scores'])+GB)[0]-max((logs(x['arms'][a]['scores'])+GB)[1:]))) for a in ARMS},timestamps={a:at[x['arms'][a]['request_id']]['created_utc'] for a in ARMS},body_hashes={a:x['arms'][a]['body_sha256'] for a in ARMS})
            detail.append(rec)
        joint=[dict(GT=k[0],F_raw_correct=k[1],P_raw_correct=k[2],F_final_correct=k[3],P_final_correct=k[4],n=n) for k,n in sorted(c.items())]
        bypatient=[]
        for sid in sorted({x['sid'] for x in z}):
            sub=[x for x in z if x['sid']==sid];bypatient.append(dict(sid=sid,n=len(sub),raw=pair_summary(sub,'F4','P90','raw'),final=pair_summary(sub,'F4','P90','PriorG')))
        order=sorted(full,key=lambda x:(at[x['arms']['B']['request_id']]['created_utc'],x['id']));ranks={x['id']:i for i,x in enumerate(order)};batch=[]
        for q in range(4):
            sub=[x for x in z if min(3,4*ranks[x['id']]//len(order))==q]
            batch.append(dict(time_quartile=q+1,n=len(sub),patients=len({x['sid'] for x in sub}),raw=pair_summary(sub,'F4','P90','raw'),final=pair_summary(sub,'F4','P90','PriorG')))
        kinds={k:dict(n=len(v:=[x for x in detail if x['panel']==panel and x['kind']==k]),GT=dict(Counter(x['GT'] for x in v))) for k in sorted({x['kind'] for x in detail if x['panel']==panel})}
        summaries[panel]=dict(full_n=len(full),common_core_n=len(z),GT=dict(Counter(y)),metrics=met,original=original,full_metrics=full_summary,post_changes=post,class_transitions=transitions,joint_correctness=joint,kind_counts=kinds,score_patterns=patterns,patients=bypatient,time_quartiles=batch,auc=auc(z),
            pairs={f'{a}-F4/{m}':pair_summary(z,'F4',a,m) for a in ('P90','B','Q90') for m in METHODS},
            leave_one_patient_net={m:[dict(sid=p['sid'],net=pair_summary(z,'F4','P90',m)['net']-p['raw' if m=='raw' else 'final']['net']) for p in bypatient] for m in ('raw','PriorG')})
    assert summaries['natural']['common_core_n']==167
    assert [summaries['natural']['metrics'][a][m]['correct'] for a,m in [('F4','raw'),('P90','raw'),('F4','PriorG'),('P90','PriorG')]]==[120,127,135,137]
    cases=[]
    for kind in ('raw_gain_retained','raw_gain_both_final_correct','raw_gain_both_final_wrong','raw_gain_reversed','raw_harm_erased','raw_harm_retained','final_only_rescue','final_only_harm'):
        pool=[x for x in detail if x['kind']==kind]
        if pool:cases.append(min(pool,key=lambda x:h('091/case/'+x['id'])))
    p078=ROOT/'outputs/078_component_ablation/predictions.jsonl';r078=lines(p078);assert len(r078)==384
    check078=dict(n=384,prior_G_label_differences=sum(x['methods']['TS_prior']['label']!=x['methods']['TS_PriorG']['label'] for x in r078))
    assert check078['prior_G_label_differences']==0
    result=dict(created_utc=now(),panels=summaries,frozen_parameters=dict(reference=COUNTS,calibration=CAL,G=G,prior_bias=PB.tolist(),PriorG_bias=GB.tolist(),S_min_ratio_to_NS=float(math.exp(GB[1]-GB[0])),S_min_ratio_to_NA=float(math.exp(GB[2]-GB[0]))),check078=check078,source_sha256={**snapshots,**bind([p078])},interpretation='Post-hoc diagnostics, no model/threshold selected; 1000 patient bootstrap conditions on fixed responses.')
    put(OUT/'B_diagnosis.json',result);putl(OUT/'B_case_paths.jsonl',detail);put(OUT/'B_representative_cases.json',cases)
    assert bind(frozen)==snapshots
    print(canonical({p:dict(kinds=d['kind_counts'],post=d['post_changes'],auc=d['auc']) for p,d in summaries.items()}))

if __name__=='__main__':main()
