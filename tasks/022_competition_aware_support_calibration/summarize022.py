"""Read-only summaries for reporting; no selection or extra fits."""
from collections import Counter,defaultdict
import common022 as c
OUT=c.OUT/'stageA_002'
if __name__=='__main__':
    rr=c.jl(OUT/'oof_predictions.jsonl');p={(r['proposition_id'],r['repeat'],r['method']):r['verdict'] for r in rr}
    print('C_vs_G_differences',sum(p[(r['proposition_id'],r['repeat'],'G')]!=r['verdict'] for r in rr if r['method']=='C'))
    metrics=c.csvrows(OUT/'core_results.csv');pairs=c.read(OUT/'paired.json')
    for scope in ('R0','R0_020','R1'):
        for author in ('all','llm','human'):
            own=[r for r in metrics if r['scope']==scope and r['author']==author and r['method'] in ('C','U2')]
            print('RESULT',c.canonical(own));print('CI',scope,author,c.canonical(pairs[f'{scope}/{author}/C-minus-U2']['metrics']))
    trans=c.csvrows(OUT/'transitions.csv');patients=c.csvrows(OUT/'patients.csv')
    for scope in ('R0','R0_020','R1'):
        cc=[r for r in trans if r['scope']==scope and r['method']=='C'];print('TRANSITIONS',scope,{key:sum(r[key]=='True' for r in cc) for key in ('rescue','harm','W_new_false_S','new_false_S','removed_false_S')})
        own=[r for r in patients if r['scope']==scope and r['method']=='C'];print('PATIENT',scope,Counter('pos' if int(r['correct_delta'])>0 else 'neg' if int(r['correct_delta'])<0 else 'zero' for r in own))
    diag=c.csvrows(OUT/'competition_diagnostic.csv');groups=defaultdict(Counter)
    for r in diag:
        key=(r['repeat'],r['r_bin'],r['U0']);groups[key][r['event']]+=1
    print('COMPETITION',c.canonical([dict(repeat=k[0],r_bin=k[1],U0=k[2],counts=dict(v)) for k,v in sorted(groups.items())]))
