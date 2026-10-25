"""Independent arithmetic/coverage checks over completed002 outputs, no API."""
from collections import Counter
import core024 as c
def run():
    a=c.OUT/'analysis_001';rows=c.csvread(c.OUT/'preparation_001/cohort.csv');truth={r['proposition_id']:r for r in rows}
    m=c.read(a/'metrics.json');p=c.read(a/'paired.json');coh=c.read(a/'comparison_cohorts.json');ts=c.csvread(a/'transitions.csv');checks=0
    for key,x in m.items():
        mat=x['confusion_matrix'];n=sum(sum(r) for r in mat);correct=sum(mat[i][i] for i in range(3));fs=mat[1][0]+mat[2][0]
        c.require(n==x['n']==x['counts']['n'] and correct==x['counts']['correct'] and fs==x['counts']['false_s'],'Confusion/count mismatch '+key)
        c.require(abs(correct/n-x['percent_agreement'])<1e-12,'PA mismatch');checks+=1
    for model in c.MODELS:
        for author in ('all','human','llm'):
            rr=[r for r in ts if r['model']==model and (author=='all' or r['author_type']==author)];ct=Counter(r['RHW'] for r in rr)
            key=f'{model}/{author}/U2-minus-U0';q=p[key]
            c.require(ct['R']-ct['H']==q['net_correct'],'Rescue/harm net mismatch')
            c.require(ct['H']+ct['W']==q['candidate']['counts']['false_s']-q['baseline']['counts']['false_s'],'FalseS identity mismatch')
            c.require(len(rr)==coh[key]['valid_n'],'RHW cohort differs');checks+=1
    preds={k:{r['proposition_id']:r for r in c.csvread(a/f'predictions_{k}.csv')} for k in c.MODELS}
    for key,q in p.items():
        parts=key.split('/');model,author,comp=parts
        if model=='qwen-minus-deepseek':bp=preds['deepseek'];cp=preds['qwen'];base=cand=comp
        else:cand,base=comp.split('-minus-');bp=cp=preds[model]
        full=[r for r in rows if author=='all' or r['author_type']==author]
        included=[r for r in full if bp[r['proposition_id']][base] in c.LABELS and cp[r['proposition_id']][cand] in c.LABELS]
        c.require([r['proposition_id'] for r in included]==coh[key]['included_ids'],'Comparison coverage mismatch '+key)
        delta=sum(int(cp[r['proposition_id']][cand]==r['human_gt'])-int(bp[r['proposition_id']][base]==r['human_gt']) for r in included)
        c.require(delta==q['net_correct'],'Pair net mismatch')
        c.require(coh[key]['expected_n']==coh[key]['valid_n']+coh[key]['missing_n'],'Missing denominator mismatch');checks+=1
    print(c.canonical(dict(checks=checks,comparison_cohorts=len(p),study_api_calls=0,status='execution_self_check_pass')))
if __name__=='__main__':run()
