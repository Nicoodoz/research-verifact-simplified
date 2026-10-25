"""Deterministic response curves, exact switch states and patient sensitivity; no fitting."""
from pathlib import Path
import argparse
from collections import Counter
import numpy as np
import common023 as c

def intervals(flags):
    result=[];start=None
    for i,flag in enumerate(list(flags)+[False]):
        if flag and start is None:start=i
        if not flag and start is not None:result.append([c.GRID[start],c.GRID[i-1]]);start=None
    return result

def shape(grid,exact):
    here=grid[200];near=[r['PA']>=here['PA']-.01-1e-12 and r['MCC']>=here['MCC']-.02-1e-12 for r in grid]
    region=next(span for span in intervals(near) if span[0]<=2<=span[1]);ix=[r for r in grid if region[0]<=r['lambda_value']<=region[1]]
    high={};joint=np.ones(len(grid),dtype=bool)
    for key,tolerance in [('PA',.01),('MCC',.02)]:
        maximum=max(r[key] for r in exact);flags=[r[key]>=maximum-tolerance-1e-12 for r in grid];joint&=flags
        stages=[]
        for i,r in enumerate(exact):
            if abs(r[key]-maximum)<1e-12:stages.append(dict(start=r['lambda_value'],end=exact[i+1]['lambda_value'] if i+1<len(exact) else 4,end_exclusive=i+1<len(exact)))
        high[key]=dict(exact_maximum=maximum,highest_state_intervals=stages,high_grid_regions=intervals(flags),at_2=here[key],gap_at_2=maximum-here[key])
    return dict(near_U2_grid_region=region,near_region_false_S_range=[min(r['false_S'] for r in ix),max(r['false_S'] for r in ix)],high=high,joint_high_grid_regions=intervals(joint))

def run(out):
    c.require(not out.exists(),'Output directory exists');c.check(c.OUT/'preparation_001')
    rows=c.jl(c.OUT/'preparation_001/scores.jsonl');allz=c.logs([r['scores'] for r in rows]);switches=[]
    for r,z in zip(rows,allz):switches.append(dict(proposition_id=r['proposition_id'],source=r['source'],repeat=r['repeat'],subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],**c.switching(z)))
    swmap={(r['proposition_id'],r['repeat']):r for r in switches}
    dense=[];exactrows=[];patientrows=[];leaverows=[];local=[];localpatients=[];platforms=[];refs=[];summary={};ids={};matrices={}
    local_lams=sorted({2.0,*[2-d for d in (.01,.05,.1,.25,.5)],*[2+d for d in (.01,.05,.1,.25,.5)]})
    for group in c.GROUPS:
        rr=c.subset(rows,group);c.require(len({r['proposition_id'] for r in rr})==len(rr),'Repeated claims in group')
        z=c.logs([r['scores'] for r in rr]);base0=c.decode(z,0);base2=c.decode(z,2);baseB=np.array([c.LABELS.index(r['B']) for r in rr]);pred=np.array([c.decode(z,lam) for lam in c.GRID],dtype=np.uint8)
        ids[group]=[r['proposition_id'] for r in rr];matrices[group]=pred
        ss=[swmap[(r['proposition_id'],r['repeat'])] for r in rr];times=sorted({0.,4.,*[r['first_S_lambda'] for r in ss if r['first_S_lambda'] is not None]})
        summary[group]=dict(n=len(rr),patients=len({r['subject_id'] for r in rr}),switch_counts=dict(Counter(r['status'] for r in ss)),authors={})
        def group_measure(ix):
            cc=[rr[i] for i in ix];cache={}
            def measure(p):
                key=tuple(p[ix].tolist())
                if key not in cache:cache[key]=c.point(cc,p[ix],base0[ix],baseB[ix])
                return dict(cache[key])
            return measure
        for author in ('all','human','llm'):
            ix=[i for i,r in enumerate(rr) if author=='all' or r['author_type']==author];measure=group_measure(ix)
            own=[dict(group=group,author=author,lambda_value=lam,**measure(p)) for lam,p in zip(c.GRID,pred)];dense.extend(own)
            ex=[dict(group=group,author=author,lambda_value=lam,**measure(c.decode(z,lam))) for lam in times];exactrows.extend(ex)
            sh=shape(own,ex);summary[group]['authors'][author]=sh
            relevant=[ss[i]['first_S_lambda'] for i in ix if ss[i]['first_S_lambda'] is not None];below=[t for t in relevant if t<=2];above=[t for t in relevant if t>2]
            platform=dict(group=group,author=author,start=max(below) if below else 0.,end=min(above) if above else 4.,end_exclusive=bool(above),labels_at_two_unchanged=True);platforms.append(platform);sh['exact_label_plateau']=platform
            at2=measure(base2)
            for lam in local_lams:
                p=c.decode(z,lam);v=measure(p);local.append(dict(group=group,author=author,lambda_value=lam,label_changes_vs2=int(sum(p[ix]!=base2[ix])),delta_correct_vs2=v['correct']-at2['correct'],delta_PA_vs2=v['PA']-at2['PA'],delta_MCC_vs2=v['MCC']-at2['MCC'],delta_false_S_vs2=v['false_S']-at2['false_S'],**v))
            cc=[rr[i] for i in ix]
            for name in ('B','V_raw','O','Always_S'):
                labels=np.array([c.LABELS.index(rr[i][name]) if name!='Always_S' else 0 for i in ix]);m=c.point(cc,labels,labels,baseB[ix])
                for key in ('rescue','harm','wrong_to_falseS','delta_correct_U0'):m.pop(key)
                refs.append(dict(group=group,author=author,method=name,**m))
        for sid in sorted({r['subject_id'] for r in rr}):
            ix=[i for i,r in enumerate(rr) if r['subject_id']==sid];measure=group_measure(ix);at2=measure(base2)
            for lam,p in zip(c.GRID,pred):patientrows.append(dict(group=group,subject_id=sid,lambda_value=lam,**measure(p)))
            for lam in local_lams:
                p=c.decode(z,lam);v=measure(p);localpatients.append(dict(group=group,subject_id=sid,lambda_value=lam,label_changes_vs2=int(sum(p[ix]!=base2[ix])),delta_correct_vs2=v['correct']-at2['correct'],delta_MCC_vs2=v['MCC']-at2['MCC'],**v))
            # Pooled stays descriptive; keep all cohort-specific leave-one-out curves.
            if group!='pooled_R0':
                other=[i for i,r in enumerate(rr) if r['subject_id']!=sid];measure=group_measure(other)
                for lam,p in zip(c.GRID,pred):leaverows.append(dict(group=group,excluded_patient=sid,lambda_value=lam,**measure(p)))
        print('Completed curves:',group,flush=True)
    out.mkdir(parents=True)
    for group,pred in matrices.items():np.save(out/('predictions_'+group+'.npy'),pred,allow_pickle=False)
    c.write(out/'prediction_ids.json',ids);c.write(out/'summary.json',summary);c.lines(out/'switches.jsonl',switches)
    for name,data in [('dense_grid',dense),('exact_states',exactrows),('patient_curves',patientrows),('leave_one_out_curves',leaverows),('local_sensitivity',local),('patient_local_sensitivity',localpatients),('exact_plateaus',platforms),('reference_metrics',refs)]:c.csvwrite(out/(name+'.csv'),data)
    c.write(out/'execution.json',dict(grid_points=401,step=.01,grid_start=0,grid_end=4,unique_claims=1529,score_observations=2408,fixed_lambda=2,lambda_reselected=False,new_API_calls=0,cost_cny=0,reserved_test_used=False,bootstrap=False,no_new_winner=True))
    c.seal(out,[c.OUT/'preparation_001/manifest.json',c.OUT/'protocol_001.md'],[Path(__file__),c.TASK/'common023.py']);print(c.canonical({g:summary[g]['authors']['all'] for g in c.GROUPS}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=c.OUT/'analysis_001');run(p.parse_args().output)
