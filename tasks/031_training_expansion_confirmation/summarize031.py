"""Mechanical report tables from completed confirmation only; no winner selection."""
from collections import Counter
import common031 as c
def run():
    out=c.OUT/'summary_001';c.require(not out.exists(),'Summary exists');analysis=c.OUT/'analysis_001';metrics=c.read(analysis/'metrics.json');pairs=c.read(analysis/'paired.json');matched=c.read(analysis/'matched.json');pred=c.csvread(analysis/'predictions.csv');patient=c.csvread(analysis/'patients.csv');trans=c.csvread(analysis/'transitions.csv');names=[e+'_'+m for e in ('before','after') for m in 'ABCD'];summary={}
    for name in names:summary[name]=metrics['all/'+name]
    deltas={};comparisons=[('before_'+m,'after_'+m) for m in 'ABCD']+[('after_A','after_C'),('after_B','after_D'),('after_A','after_B'),('after_C','after_D')]
    bypatient={(r['subject_id'],r['method']):r for r in patient}
    for before,after in comparisons:
        key=after+'-minus-'+before;mm={k:metrics['all/'+after][k]-metrics['all/'+before][k] for k in ('correct','R','H','W','risk','false_S','PA','MCC','AC1')};ds=[int(bypatient[s,after]['correct'])-int(bypatient[s,before]['correct']) for s in sorted({r['subject_id'] for r in patient})];rr=[r for r in trans if r['comparison']==key];mm.update(patient_direction=dict(positive=sum(x>0 for x in ds),negative=sum(x<0 for x in ds),ties=sum(x==0 for x in ds)),transitions={f:sum(r[f]=='True' for r in rr) for f in ('blocked_falseS','lost_R','recovered_R','new_falseS','wrong_to_correct','correct_to_wrong')},paired=pairs['all/'+key]);deltas[key]=mm
    out.mkdir();c.put(out/'summary.json',dict(confirmation_n=len(pred),GT_counts=dict(Counter(r['GT'] for r in pred)),eight_results=summary,deltas=deltas,matched=matched,coverage=c.read(analysis/'coverage.json'),cost=c.read(c.OUT/'costs_001/costs.json'),scientific_conclusion_not_automated=True))
    table=['|方案|正确/N|PA|MCC|AC1|R/H/W|新增false-S|R保留率|总false-S|','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name in ['U0','U2',*names]:
        m=metrics['all/'+name];ret='不可评估' if m['rescue_retention'] is None else f"{m['rescue_retention']:.1%}";table.append(f"|{name}|{m['correct']}/{m['n']}|{m['PA']:.2%}|{m['MCC']:.4f}|{m['AC1']:.4f}|{m['R']}/{m['H']}/{m['W']}|{m['risk']}|{ret}|{m['false_S']}|")
    c.write_text(out/'main_table.md','\n'.join(table)+'\n');c.put(out/'manifest.json',dict(inputs={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [analysis/'manifest.json',c.OUT/'costs_001/manifest.json',c.TASK/'summarize031.py']},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('031 mechanical report tables prepared')
if __name__=='__main__':run()
