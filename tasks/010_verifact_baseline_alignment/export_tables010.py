"""Compact research tables directly from the existing unified metric objects."""
from pathlib import Path
import alignment_common as s

if __name__=='__main__':
    analysis=s.OUT/'analysis_001';s.check(analysis)
    system=s.read_json(analysis/'system_reference_metrics.json')
    current=s.read_json(analysis/'metrics.json')
    results=[];classes=[];contrasts=[]
    for name,by_author in system.items():
        for author,m in by_author.items():
            results.append(dict(layer='same_cohort_system_reference',condition=name,author=author,n=m['n'],PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc']))
            classes.extend(dict(layer='same_cohort_system_reference',condition=name,author=author,label=label,**v) for label,v in m['per_class'].items())
    for author,section in current.items():
        for name,m in section['metrics'].items():
            if 'status' in m:
                results.append(dict(layer='contemporaneous_same_judge',condition=name,author=author,n=m['expected_n'],PA=None,AC1=None,MCC=None))
            else:
                results.append(dict(layer='contemporaneous_same_judge',condition=name,author=author,n=m['n'],PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc']))
                classes.extend(dict(layer='contemporaneous_same_judge',condition=name,author=author,label=label,**v) for label,v in m['per_class'].items())
        for name,c in section['contrasts'].items():
            if 'metrics' in c:
                contrasts.extend(dict(author=author,contrast=name,metric=metric,delta=v['delta'],low=v['ci95'][0],high=v['ci95'][1]) for metric,v in c['metrics'].items())
    out=s.OUT/'tables_001';out.mkdir(exist_ok=False)
    s.pilot.write_csv(out/'core_results.csv',results)
    s.pilot.write_csv(out/'per_class.csv',classes)
    s.pilot.write_csv(out/'paired_differences.csv',contrasts)
    rows=['|层次|条件|作者|N|PA|AC1|MCC|','|---|---|---|---:|---:|---:|---:|']
    fmt=lambda x:'受阻' if x is None else f'{x:.4f}'
    rows.extend(f"|{r['layer']}|{r['condition']}|{r['author']}|{r['n']}|{fmt(r['PA'])}|{fmt(r['AC1'])}|{fmt(r['MCC'])}|" for r in results)
    (out/'core_results.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    s.seal(out,[analysis/'manifest.json'],[Path(__file__)])
    print('\n'.join(rows))
