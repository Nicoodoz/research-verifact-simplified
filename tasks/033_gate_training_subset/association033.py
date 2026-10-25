"""Descriptive patient inclusion associations, conditional on training size/test patient."""
from collections import defaultdict
import numpy as np
import common033 as s

def run():
    out=s.OUT/'association_001';s.require(not out.exists(),'Association exists');rows=s.lines(s.PREP/'rows_selection_blind.jsonl');old=[r for r in rows if r['partition']=='original16'];ff=s.candidate_rows(old);subjects=sorted({r['subject_id'] for r in ff});rank=s.read(s.OUT/'historical_001/ranking.json');profiles=[];inc=[];influence={}
    for sid in sorted({r['subject_id'] for r in old}):
        cc=[r for r in ff if r['subject_id']==sid];rr=[r for r in old if r['subject_id']==sid];profile=dict(subject_id=sid,group=rr[0]['group'],**s.training_summary([sid],old,ff));profile.update({'mean_'+k:float(np.mean([r['features'][k] for r in cc])) if cc else None for k in s.c.FEATURES['D']});profile['U2']=s.point(rr,[r['u2'] for r in rr]);profiles.append(profile)
    for method in ('A','B','D'):
        for sid in subjects:
            eligible=[]
            for k in (3,5,8,11,14):
                rs=[r for r in rank if r['method']==method and r['k']==k];yes=[r for r in rs if sid in r['train_patients']];no=[r for r in rs if sid not in r['train_patients']]
                if not yes or not no:continue
                record=dict(method=method,training_patient=sid,k=k,n_in=len(yes),n_out=len(no),adequate_cells=len(yes)>=3 and len(no)>=3)
                for key in ('robust_gain_per100R','rescue_retention','risk','MCC','correct','threshold','global_gain_R','A16_gain_R'):record[key+'_in_minus_out']=float(np.mean([r[key] for r in yes])-np.mean([r[key] for r in no]))
                inc.append(record)
                if record['adequate_cells']:eligible.append(record['robust_gain_per100R_in_minus_out'])
            influence[method+'/'+sid]=dict(equal_k_mean_effect=float(np.mean(eligible)) if eligible else 0.,strata=len(eligible),positive_strata=sum(v>0 for v in eligible),negative_strata=sum(v<0 for v in eligible),sparse_excluded=True)
    unit=s.csvread(s.HIST/'unit_metrics.csv');modelsets=s.read(s.HIST/'model_index.json');unique={(r['model_id'],r['held_patient']):r for r in unit};base={r['held_patient']:float(r['correct']) for r in unit if r['k']=='14' and r['method']=='A'};strata=defaultdict(list)
    for r in unique.values():strata[r['method'],r['held_patient'],int(r['k'])].append(r)
    held=[]
    for (method,test,k),rr in strata.items():
        for sid in subjects:
            if sid==test:continue
            yes=[r for r in rr if sid in modelsets[r['model_id']]['training_patients']];no=[r for r in rr if sid not in modelsets[r['model_id']]['training_patients']]
            if not yes or not no:continue
            held.append(dict(method=method,held_patient=test,held_group=next(r['group'] for r in old if r['subject_id']==test),k=k,training_patient=sid,n_in=len(yes),n_out=len(no),adequate_cells=len(yes)>=3 and len(no)>=3,correct_in_minus_out=np.mean([float(r['correct'])-base[test] for r in yes])-np.mean([float(r['correct'])-base[test] for r in no]),risk_in_minus_out=np.mean([float(r['risk']) for r in yes])-np.mean([float(r['risk']) for r in no]),retention_in_minus_out=np.mean([float(r['rescue_retention']) for r in yes if r['rescue_retention']!=''])-np.mean([float(r['rescue_retention']) for r in no if r['rescue_retention']!=''])))
    sources=[]
    for method in ('A','B','D'):
        for n026 in sorted({r['train_026'] for r in rank if r['k']==5}):
            rr=[r for r in rank if r['method']==method and r['k']==5 and r['train_026']==n026];sources.append(dict(method=method,k=5,train_026=n026,sets=len(rr),**{k+'_mean':np.mean([r[k] for r in rr]) for k in ('train_candidates','train_R_fraction','rescue_retention','risk','correct','MCC','A16_gain_R','global_gain_R','robust_gain_per100R')}))
    out.mkdir();s.csvwrite(out/'patient_profiles.csv',profiles);s.put(out/'patient_profiles.json',profiles);s.csvwrite(out/'common_panel_inclusion_by_size.csv',inc);s.put(out/'influence.json',influence);s.csvwrite(out/'original_held_adjusted_inclusion.csv',held);s.csvwrite(out/'common_panel_source_comparison.csv',sources);s.put(out/'manifest.json',dict(created_utc=s.now(),files={p.name:s.sha(p) for p in out.iterdir() if p.is_file()},causal=False,confirmation_GT_used=False));s.status('patient associations complete',patients=len(profiles))

if __name__=='__main__':run()
