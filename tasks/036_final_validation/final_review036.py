"""Compact existing paired estimates and parser exceptions for manuscript review."""
import common036 as c
def main():
    table=[];classes=[];confusions=[]
    for rn in ('R0','R1','R0_repeat_subset'):
        folder=c.OUT/'analysis_001'/rn;m=c.read(folder/'metrics.json')
        for key,v in m.items():
            scope,method=key.split('/')
            for i,label in enumerate(c.LABELS):
                classes.append(dict(round=rn,scope=scope,method=method,label=label,**v['per_class'][label]))
                confusions.append(dict(round=rn,scope=scope,method=method,GT=label,predicted_S=v['confusion_matrix'][i][0],predicted_NS=v['confusion_matrix'][i][1],predicted_NA=v['confusion_matrix'][i][2]))
        for key,p in c.read(folder/'paired.json').items():
            scope,contrast=key.split('/');new,base=contrast.split('-vs-');metric=p['metrics'];extra=p.get('probability_and_risk',{})
            table.append(dict(round=rn,scope=scope,contrast=contrast,delta_correct=m[scope+'/'+new]['correct']-m[scope+'/'+base]['correct'],delta_false_S=m[scope+'/'+new]['false_S']-m[scope+'/'+base]['false_S'],PA_delta=metric['percent_agreement']['delta'],PA_ci95=metric['percent_agreement']['ci95'],MCC_delta=metric['mcc']['delta'],MCC_ci95=metric['mcc']['ci95'],AC1_delta=metric['gwet_ac1']['delta'],AC1_ci95=metric['gwet_ac1']['ci95'],NLL=extra.get('NLL'),Brier=extra.get('Brier'),FSR=p.get('false_S_rate')))
    c.csvwrite(c.OUT/'paired_statistics.csv',table)
    c.csvwrite(c.OUT/'class_performance.csv',classes);c.csvwrite(c.OUT/'confusion_matrices.csv',confusions)
    equivalents=[]
    for rn in ('R0','R1','R0_repeat_subset'):
        rows=c.csvread(c.OUT/'analysis_001'/rn/'predictions.csv')
        for left,right in [('U2','U2_T'),('U2','Task_T'),('U2','Robust_T'),('U0','Std_T'),('Joint_NLL','U4')]:
            changes=sum(r[left]!=r[right] for r in rows);assert changes==0
            equivalents.append(dict(round=rn,first=left,second=right,n=len(rows),label_changes=changes))
    c.csvwrite(c.OUT/'final_label_equivalence.csv',equivalents)
    repeat0=c.csvread(c.OUT/'analysis_001/R0_repeat_subset/predictions.csv');repeat1=c.csvread(c.OUT/'analysis_001/R1/predictions.csv')
    assert {r['id'] for r in repeat0}=={r['id'] for r in repeat1} and len(repeat0)==len(repeat1)==444
    invalid=[dict(request_id=r['request_id'],round=r['round'],role=r['role'],id=r['proposition_id'],parsed=r['parsed'],receipt=r['receipt']) for r in c.lines(c.OUT/'predictions_blind_001/normalized.jsonl') if r['parsed']['status'] not in ('valid','valid_with_format_anomaly')]
    c.put(c.OUT/'core_invalid_details.json',invalid)
    for r in table:
        if r['round']=='R0' and ((r['scope']=='all' and r['contrast'] in ('Std_M-vs-U2','Std_V-vs-U2','U2_T-vs-U2')) or (r['scope'] in ('human','llm') and r['contrast'] in ('U2-vs-U0','Gate_A-vs-U2'))):print(r)
    for r in invalid:print('INVALID',r['round'],r['role'],r['id'],r['parsed'].get('errors'))
if __name__=='__main__':main()
