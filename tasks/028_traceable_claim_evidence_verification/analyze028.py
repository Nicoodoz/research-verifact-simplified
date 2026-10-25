"""Fixed-rule full-cohort evaluation, complete references and paired conflict diagnosis."""
import argparse,socket
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import common028 as c

def load():
    jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);counts=Counter(a['request_id'] for a in attempts);c.require(not (c.OUT/'live.lock').exists(),'API active');c.require(all(j['request_id'] in term or counts[j['request_id']]>=3 for j in jobs),'Incomplete calls')
    old=[r for r in c.lines(c.ROOT/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl') if r['group']=='024_D'];new=[];ns={r['proposition_id']:r['scores'] for r in c.lines(c.ROOT/'outputs/026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl') if r['model_key']=='deepseek' and r['arm']=='S'}
    for r in c.csvread(c.ROOT/'outputs/026_frozen_sd_patient_transfer/preparation_001/cohort.csv'):
        sc=ns[r['proposition_id']];u0=int(c.risk.decode(c.risk.logs(sc),0));u2=int(c.risk.decode(c.risk.logs(sc),2));new.append(dict(r,scores=sc,u0=u0,u2=u2,candidate=u0!=0 and u2==0))
    candidates={r['proposition_id']:r for r in c.read(c.OUT/'preparation_001/candidates.json')};parsed={(j['proposition_id'],j['arm']):term.get(j['request_id'],dict(status='invalid_core_fields',keep=False,errors=['no_HTTP200_after_3_attempts'])) for j in jobs};rows=[]
    for g,rs in [('025',old),('026',new)]:
        for r in rs:
            pid=r['proposition_id'];p=r['u0'];q=dict(r,group=g,SD=p,repeat=p,trace=p,valid_pair=True)
            if r['candidate']:
                item=candidates[pid];c.require(item['group']==g and item['GT']==r['human_gt'],'Candidate alignment');q['SD']=0 if item['keep'] else p;q['SD_probability']=item['SD']
                for arm in ('repeat','trace'):q[arm]=0 if parsed[pid,arm]['keep'] else p
                q['valid_pair']=all(parsed[pid,a]['status'] in c.VALID for a in ('repeat','trace'))
            rows.append(q)
    c.require(len(rows)==1529 and sum(r['candidate'] for r in rows)==155,'Wrong cohort');return jobs,attempts,parsed,rows

def transitions(rows,base,cand):
    return dict(n=len(rows),blocked_previous_falseS=sum(r[base]==0 and r[cand]!=0 and r['human_gt']!='Supported' for r in rows),lost_previous_R=sum(r[base]==0 and r[cand]!=0 and r['human_gt']=='Supported' for r in rows),recovered_missed_R=sum(r[base]!=0 and r[cand]==0 and r['human_gt']=='Supported' for r in rows),new_falseS_from_previous_reject=sum(r[base]!=0 and r[cand]==0 and r['human_gt']!='Supported' for r in rows),wrong_to_correct=sum(c.LABELS[r[base]]!=r['human_gt'] and c.LABELS[r[cand]]==r['human_gt'] for r in rows),correct_to_wrong=sum(c.LABELS[r[base]]==r['human_gt'] and c.LABELS[r[cand]]!=r['human_gt'] for r in rows))

def references(rows):
    u0=np.array([r['u0'] for r in rows]);u2=np.array([r['u2'] for r in rows]);sd=np.array([r['SD'] for r in rows]);repeat=np.array([r['repeat'] for r in rows]);times,gp=c.frontier.global_states(rows)
    probabilities=[r['SD_probability'] for r in rows if r['candidate']];thresholds=[float(np.nextafter(max(probabilities),np.inf)),*sorted(set(probabilities),reverse=True)];sp=[sd]
    for t in thresholds:sp.append(np.array([0 if r['candidate'] and r['SD_probability']>=t else r['u0'] for r in rows]))
    return dict(global_lambda=gp,SD=np.array(sp),repeat=np.array([u0,repeat,u2])),times,thresholds

def matched(rows,refs,weights=None):
    target=np.array([r['trace'] for r in rows]);tr,tf=c.frontier.counts(rows,target,weights);out={}
    for name,pp in refs.items():rr,ff=c.frontier.counts(rows,pp,weights);out[name]=c.frontier.matched(ff,rr,float(tf[0]),float(tr[0]))
    return out

def conflict_analysis(rows):
    source=c.read(c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002/conflicts.json');lookup={r['proposition_id']:r for r in rows};ledger=[];summary={}
    for group in ('025','026'):
        gs=source[group]['mixed_groups'];ids=set(pid for g in gs for pid in g['ids']);subset=[lookup[p] for p in ids];sm={name:dict(binary_errors=sum((r[name]==0)!=(r['human_gt']=='Supported') for r in subset),R=sum(r[name]==0 and r['human_gt']=='Supported' for r in subset),risk=sum(r[name]==0 and r['human_gt']!='Supported' for r in subset)) for name in ('SD','repeat','trace')};pairs={name:0 for name in ('SD','repeat','trace')};new=0;reverse=0
        for gi,g in enumerate(gs):
            members=[lookup[p] for p in g['ids']]
            for R in members:
                if R['human_gt']!='Supported':continue
                for F in members:
                    if F['human_gt']=='Supported' or R['subject_id']==F['subject_id']:continue
                    success={m:R[m]==0 and F[m]!=0 for m in pairs}
                    for m,v in success.items():pairs[m]+=int(v)
                    newly=success['trace'] and not success['SD'];new+=int(newly);reverse+=int(R['trace']!=0 and F['trace']==0)
                    ledger.append(dict(group=group,conflict_group=gi,R_id=R['proposition_id'],risk_id=F['proposition_id'],R_patient=R['subject_id'],risk_patient=F['subject_id'],new_trace_correct_pair_vs_SD=bool(newly),**{m:bool(v) for m,v in success.items()}))
        summary[group]=dict(n=len(subset),groups=len(gs),methods=sm,cross_patient_correct_pairs=pairs,new_correct_pairs_vs_SD=new,reverse_wrong_pairs=reverse)
    return summary,ledger

def run(out):
    socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(RuntimeError('028 evaluation offline'));jobs,attempts,parsed,rows=load();c.require(not out.exists(),'New output required');out.mkdir(parents=True)
    methods={'U0':'u0','U2':'u2','SD':'SD','repeat':'repeat','trace':'trace'};metrics={};paired={};summary={};curves=[];patients=[];trans={};candidate_records=[];normalized=[]
    for j in jobs:normalized.append(dict(request_id=j['request_id'],proposition_id=j['proposition_id'],group=j['group'],arm=j['arm'],**parsed[j['proposition_id'],j['arm']]))
    for group in ('025','026','pooled'):
        rr=[r for r in rows if group=='pooled' or r['group']==group];refs,times,thresholds=references(rr);mm=matched(rr,refs);subjects=sorted(set(r['subject_id'] for r in rr));ix=np.array([subjects.index(r['subject_id']) for r in rr]);draw={k:[] for k in refs};loo=[]
        for seed in range(1000):
            w=np.bincount(np.random.RandomState(seed).choice(len(subjects),len(subjects),replace=True),minlength=len(subjects))[ix].astype(float);m=matched(rr,refs,w)
            for k in refs:draw[k].append(m[k]['R_gain_vs_mixture'])
        for sid in subjects:
            w=np.array([r['subject_id']!=sid for r in rr],dtype=float);loo.append(dict(excluded_patient=sid,comparisons=matched(rr,refs,w)))
        summary[group]=dict(matched=mm,ci95={k:np.percentile(v,[2.5,97.5]).tolist() for k,v in draw.items()},leave_one_patient_out=loo,patients=subjects,bootstrap_iterations=1000)
        for name,pp in refs.items():
            for i,p in enumerate(pp):curves.append(dict(group=group,reference=name,index=i,parameter=times[i] if name=='global_lambda' else (None if i==0 else thresholds[i-1]) if name=='SD' else None,**c.risk.point(rr,p)))
        for author in ('all','human','llm'):
            ss=[r for r in rr if author=='all' or r['author_type']==author]
            for name,key in methods.items():metrics[group+'/'+author+'/'+name]=c.risk.point(ss,[r[key] for r in ss])
            for base in ('SD','repeat','u2'):
                trans[group+'/'+author+'/trace-minus-'+base]=transitions([r for r in ss if r['candidate']],base,'trace')
                paired[group+'/'+author+'/trace-minus-'+base]=c.risk.paired_compare(ss,c.risk.prediction(ss,[r[base] for r in ss]),c.risk.prediction(ss,[r['trace'] for r in ss]))
        for sid in subjects:
            ss=[r for r in rr if r['subject_id']==sid]
            for name,key in methods.items():patients.append(dict(group=group,subject_id=sid,method=name,**c.risk.point(ss,[r[key] for r in ss])))
    for r in rows:
        if not r['candidate']:continue
        p=r['proposition_id'];z={a:parsed[p,a] for a in ('repeat','trace')};candidate_records.append(dict(group=r['group'],proposition_id=p,subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],RHW='R' if r['human_gt']=='Supported' else 'H' if c.LABELS[r['u0']]==r['human_gt'] else 'W',**{name:c.LABELS[r[key]] for name,key in methods.items()},repeat_core_status=z['repeat']['status'],trace_core_status=z['trace']['status'],trace_quality=z['trace'].get('fully_traceable',False),requirements=len(z['trace'].get('rows',[])),trace_relation_only_keep=z['trace'].get('relation_only_keep',False),trace_citation_veto=bool(z['trace'].get('relation_only_keep',False) and not z['trace']['keep']),pair_valid=r['valid_pair']))
    conflict,cl=c.conflict_analysis(rows) if hasattr(c,'conflict_analysis') else conflict_analysis(rows)
    tracevalid=sum(v['status'] in c.VALID for (pid,a),v in parsed.items() if a=='trace');quality=sum(v.get('fully_traceable',False) for (pid,a),v in parsed.items() if a=='trace');pair=[r for r in rows if r['valid_pair']]
    sensitivity={m:c.risk.point(pair,[r[k] for r in pair]) for m,k in methods.items()};c.put(out/'paired_valid_sensitivity.json',dict(n=len(pair),excluded_ids=[r['proposition_id'] for r in rows if not r['valid_pair']],metrics=sensitivity))
    point=metrics['pooled/all/trace'];sd=metrics['pooled/all/SD'];gain=summary['pooled'];sdcerr=sum(conflict[g]['methods']['SD']['binary_errors'] for g in conflict);rperr=sum(conflict[g]['methods']['repeat']['binary_errors'] for g in conflict);tcerr=sum(conflict[g]['methods']['trace']['binary_errors'] for g in conflict)
    checks=dict(trace_quality95=quality/155>=.95,cohort_rescue80=all(metrics[g+'/all/trace']['R']>=.8*metrics[g+'/all/U2']['R'] for g in ('025','026')),risk75_SD=point['risk']<=.75*sd['risk'],matched_gain5_all=all(v['R_gain_vs_mixture']>=5 for v in gain['matched'].values()),matched_CI_positive=all(v[0]>0 for v in gain['ci95'].values()),both_cohorts_positive=all(v['R_gain_vs_mixture']>0 for g in ('025','026') for v in summary[g]['matched'].values()),loo13=sum(all(v['R_gain_vs_mixture']>0 for v in item['comparisons'].values()) for item in gain['leave_one_patient_out'])>=13,authors_protected=all(metrics['pooled/'+a+'/trace']['correct']>=metrics['pooled/'+a+'/SD']['correct'] and metrics['pooled/'+a+'/trace']['false_S']<=metrics['pooled/'+a+'/SD']['false_S'] for a in ('human','llm')),repair_cross_patient=len(set(r['subject_id'] for r in rows if r['candidate'] and r['SD']==0 and r['trace']!=0 and r['human_gt']!='Supported'))>=2,conflict_error_gain=sdcerr-tcerr>=4 and rperr-tcerr>=2,conflict_new_cross_pairs=sum(v['new_correct_pairs_vs_SD'] for v in conflict.values())>=2)
    c.put(out/'decision.json',dict(checks={k:bool(v) for k,v in checks.items()},development_feasible=bool(all(checks.values())),stop_if_false=True,no_new_model_or_threshold=True))
    c.put(out/'metrics.json',metrics);c.put(out/'paired.json',paired);c.put(out/'matched.json',summary);c.put(out/'transitions.json',trans);c.put(out/'conflicts.json',conflict);c.csvwrite(out/'conflict_pairs.csv',cl);c.csvwrite(out/'curves.csv',curves);c.csvwrite(out/'patients.csv',patients);c.csvwrite(out/'candidates.csv',candidate_records)
    c.csvwrite(out/'predictions.csv',[dict(group=r['group'],proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],GT=r['human_gt'],**{n:c.LABELS[r[k]] for n,k in methods.items()}) for r in rows])
    with (out/'normalized.jsonl').open('x',encoding='utf-8',newline='\n') as f:
        for r in normalized:f.write(c.canonical(r)+'\n')
    c.csvwrite(out/'cost_ledger.csv',attempts);c.put(out/'costs.json',dict(cap_cny=80,total_cny=sum(a['charge_cny'] for a in attempts),unknown_reservation_cny=sum(a['charge_cny'] for a in attempts if a['charge_basis']!='peak_no_cache_usage_estimate'),by_arm={arm:sum(a['charge_cny'] for a in attempts if a['arm']==arm) for arm in ('trace','repeat')},attempts=len(attempts)))
    c.put(out/'coverage.json',dict(full_n=1529,candidates_n=155,trace_core_valid=tracevalid,trace_fully_traceable=quality,repeat_core_valid=sum(v['status'] in c.VALID for (p,a),v in parsed.items() if a=='repeat'),core_status=dict(Counter(a+':'+v['status'] for (p,a),v in parsed.items())),invalid_ids=[dict(proposition_id=p,arm=a,errors=v['errors']) for (p,a),v in parsed.items() if v['status'] not in c.VALID],citations=sum(len(r['evidence']) for (p,a),v in parsed.items() if a=='trace' for r in v.get('rows',[])),verified_citations=sum(e['valid'] for (p,a),v in parsed.items() if a=='trace' for r in v.get('rows',[]) for e in r['evidence'])))
    deps=[c.OUT/'preparation_001/manifest.json',Path(__file__),c.TASK/'common028.py',c.ROOT/'outputs/027_dual_judge_transfer_diagnosis/analysis_002/conflicts.json',c.ROOT/'outputs/025_lambda_flip_risk_separability/preparation_001/rows.jsonl',c.ROOT/'outputs/026_frozen_sd_patient_transfer/analysis_001/normalized.jsonl']+list((c.OUT/'attempts').glob('*/*.json'))
    c.put(out/'manifest.json',dict(inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in deps},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print(c.canonical(c.read(out/'decision.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();out=Path(a.output).resolve() if a.output else c.OUT/'analysis_001';c.require(out==c.OUT/'analysis_001' or out.is_relative_to(c.ROOT/'outputs/replays'),'Unsafe output');run(out)
