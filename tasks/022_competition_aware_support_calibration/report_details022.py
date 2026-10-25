"""Explicit rate and class denominators derived from the frozen002 results."""
from pathlib import Path
import common022 as c

if __name__=='__main__':
    out=c.OUT/'reporting_001';c.require(not out.exists(),'Reporting directory exists');out.mkdir()
    metrics=c.read(c.OUT/'stageA_002/metrics.json');result=[]
    for row in c.csvrows(c.OUT/'stageA_002/core_results.csv'):
        n=int(row['nonS']);m=metrics[f"{row['scope']}/{row['author']}/{row['method']}"]
        result.append(dict(scope=row['scope'],author=row['author'],method=row['method'],false_S=int(row['false_S']),GT_nonS=n,false_S_rate=int(row['false_S'])/n if n else None,**{cname+'_'+metric:m['per_class'][label][metric] for cname,label in zip(('S','NS','NA'),c.LABELS) for metric in ('precision','recall','f1')}))
    c.csvwrite(out/'risk_and_classes.csv',result)
    c.seal(out,[c.OUT/'stageA_002/manifest.json'],[Path(__file__)])
    with (c.OUT/'statistics.md').open('a',encoding='utf-8',newline='\n') as f:f.write('\n显式false-S率（分母真实非S）与三类precision/recall/F1：[risk_and_classes.csv](reporting_001/risk_and_classes.csv)。\n')
    print('Saved explicit class/risk rates for',len(result),'method/scope/author combinations.')
