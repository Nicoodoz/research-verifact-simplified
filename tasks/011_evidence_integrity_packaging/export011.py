"""Tables by author and repeat round; never pool repeats as independent claims."""
from pathlib import Path
import argparse
import study011 as s

def run(phase,out):
    source=s.OUT/f'{phase}_analysis_001';s.check(source)
    metrics=s.read_json(source/'metrics_by_round.json')
    rows=[];classes=[];paired=[]
    for rep,authors in metrics.items():
        for author,section in authors.items():
            for arm,m in section['metrics'].items():
                if 'status' in m:rows.append(dict(phase=phase,round=rep,author=author,arm=arm,status=m['status']));continue
                rows.append(dict(phase=phase,round=rep,author=author,arm=arm,n=m['n'],PA=m['percent_agreement'],AC1=m['gwet_ac1'],MCC=m['mcc'],
                    correct=sum(m['confusion_matrix'][i][i] for i in range(3)),false_supported=m['per_class']['Supported']['fp']))
                classes.extend(dict(phase=phase,round=rep,author=author,arm=arm,label=label,**v) for label,v in m['per_class'].items())
            for contrast,c in section['contrasts'].items():
                if 'metrics' in c:paired.extend(dict(phase=phase,round=rep,author=author,contrast=contrast,metric=metric,delta=v['delta'],low=v['ci95'][0],high=v['ci95'][1]) for metric,v in c['metrics'].items())
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_csv(out/'results.csv',rows)
    s.pilot.write_csv(out/'classes.csv',classes)
    s.pilot.write_csv(out/'paired.csv',paired)
    text=['|阶段|轮|作者|条件|N|正确|PA|AC1|MCC|NS/NA错判S|','|---|---:|---|---|---:|---:|---:|---:|---:|---:|']
    text.extend(f"|{r['phase']}|{r['round']}|{r['author']}|{r['arm']}|{r['n']}|{r['correct']}|{r['PA']:.4f}|{r['AC1']:.4f}|{r['MCC']:.4f}|{r['false_supported']}|" for r in rows if 'n' in r)
    (out/'results.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    s.seal(out,[source/'manifest.json'],[Path(__file__)])
    print('\n'.join(text))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=s.STAGE_CAPS);p.add_argument('--output',type=Path)
    a=p.parse_args();run(a.phase,a.output or s.OUT/f'{a.phase}_tables_001')
