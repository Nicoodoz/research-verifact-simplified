"""Descriptive patient/cohort and score-discretization summaries; never selects lambda."""
from pathlib import Path
from collections import Counter
import common023 as c

def run(out):
    c.require(not out.exists(),'Summary exists');c.check(c.OUT/'analysis_001')
    data=c.OUT/'analysis_001';patients=c.csvrows(data/'patient_curves.csv');leave=c.csvrows(data/'leave_one_out_curves.csv');local=c.csvrows(data/'patient_local_sensitivity.csv');rows=c.jl(c.OUT/'preparation_001/scores.jsonl');switches=c.jl(data/'switches.jsonl')
    results={};leave_summary=[];switch_events=[]
    for group in c.GROUPS:
        rr=c.subset(rows,group);p=[r for r in patients if r['group']==group and float(r['lambda_value'])==2]
        results[group]=dict(patient_count=len(p),lambda2_patient_deltas=[dict(subject_id=r['subject_id'],n=int(r['n']),delta_U0=int(r['delta_correct_U0']),delta_B=int(r['delta_correct_B'])) for r in p],directions={key:dict(Counter('positive' if int(r[key])>0 else 'negative' if int(r[key])<0 else 'zero' for r in p)) for key in ('delta_correct_U0','delta_correct_B')},local_directions={str(lam):dict(Counter('positive' if int(r['delta_correct_vs2'])>0 else 'negative' if int(r['delta_correct_vs2'])<0 else 'zero' for r in local if r['group']==group and float(r['lambda_value'])==lam)) for lam in (1.9,1.95,2.05,2.1,2.5)},score_saturation=dict(S100=sum(r['scores']['Supported']==100 for r in rr),some_zero=sum(0 in r['scores'].values() for r in rr),all_scores_multiple5=sum(all(v%5==0 for v in r['scores'].values()) for r in rr)))
        for sid in sorted({r['subject_id'] for r in rr}):
            own=[r for r in leave if r['group']==group and r['excluded_patient']==sid]
            if not own:continue
            at2=next(r for r in own if float(r['lambda_value'])==2);at0=next(r for r in own if float(r['lambda_value'])==0)
            maximum=max(float(r['MCC']) for r in own);maxPA=max(float(r['PA']) for r in own)
            leave_summary.append(dict(group=group,excluded_patient=sid,at2_delta_correct_U0=int(at2['delta_correct_U0']),at2_delta_MCC_U0=float(at2['MCC'])-float(at0['MCC']),highest_MCC_grid_min=min(float(r['lambda_value']) for r in own if abs(float(r['MCC'])-maximum)<1e-12),highest_MCC_grid_max=max(float(r['lambda_value']) for r in own if abs(float(r['MCC'])-maximum)<1e-12),at2_gap_to_MCC_max=maximum-float(at2['MCC']),at2_gap_to_PA_max=maxPA-float(at2['PA'])))
        # Document the score ratios immediately around2, without interpreting them as evidence quality.
        keys={(r['proposition_id'],r['repeat']) for r in rr};relevant=[r for r in switches if (r['proposition_id'],r['repeat']) in keys and r['first_S_lambda'] is not None and 1.9<r['first_S_lambda']<2.1]
        for t in sorted({r['first_S_lambda'] for r in relevant}):
            pp=[r for r in relevant if r['first_S_lambda']==t];switch_events.append(dict(group=group,first_S_lambda=t,n=len(pp),GT_counts=dict(Counter(r['GT'] for r in pp)),patients=len({r['subject_id'] for r in pp})))
    out.mkdir(parents=True);c.write(out/'patient_summary.json',results);c.csvwrite(out/'leave_one_out_summary.csv',leave_summary);c.write(out/'local_switch_events.json',switch_events)
    c.seal(out,[data/'manifest.json',c.OUT/'preparation_001/manifest.json'],[Path(__file__)])
    for g,r in results.items():print(g,c.canonical(dict(directions=r['directions'],local=r['local_directions'],patients=r['lambda2_patient_deltas'],scores=r['score_saturation'])))
    print('LEAVE',c.canonical(leave_summary));print('SWITCHES',c.canonical(switch_events))

if __name__=='__main__':run(c.OUT/'description_001')
