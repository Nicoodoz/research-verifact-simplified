"""Executor checks: isolation, budgets, provenance, fixed methods and metrics."""
import ast,json,sys,subprocess,re
from decimal import Decimal
from collections import Counter
from sklearn.metrics import confusion_matrix,accuracy_score,matthews_corrcoef,f1_score
import common094 as c
import api094,method094 as m,grounding094
def main():
    checks=[]
    def ck(v,name):
        assert v,name
        checks.append(name)
    synthetic='1. Date: test | Text: Device\n remains in place.\n2. Date: test | Text: Planned removal.'
    obj=dict(status='answered',candidates=[dict(answer='in place',time='unknown',state='present',evidence=[dict(reference_id=1,quote='Device remains in place.')])])
    tr=lambda:dict(body_text=json.dumps(dict(choices=[dict(message=dict(content=json.dumps(obj)))])))
    aligned_test=grounding094.parse(tr(),synthetic);ck(aligned_test['valid'] and aligned_test['record']['candidates'][0]['evidence'][0]['quote']=='Device\n remains in place.','whitespace restores actual source')
    obj['candidates'][0]['evidence'][0]['reference_id']=2;ck(not grounding094.parse(tr(),synthetic)['valid'],'wrong source not repaired')
    obj['candidates'][0]['evidence'][0]=dict(reference_id=1,quote='Device ... place.');ck(not grounding094.parse(tr(),synthetic)['valid'],'ellipsis not reconstructed')
    for name in ['design_freeze','runner_freeze','judge_freeze','history_sources','analysis_sources']:
        for p,h in c.read(c.OUT/(name+'.json'))['sources'].items():ck(c.sha(c.ROOT/p)==h,'unchanged '+p)
    attempts,s=api094.state();jobs=sum([c.lines(c.PRIVATE/(stage+'_jobs.jsonl')) for stage in ['preflight','generate','extract','judge']],[])
    ck(len(s)==len(jobs),'all planned physical requests complete');ck(len({j['request_id'] for j in jobs})==len(jobs),'unique logical IDs')
    total=Decimal(0)
    for a in attempts:
        req=c.read(c.ROOT/a['request_path']);rp=(c.ROOT/a['request_path']).parent/'receipt.json';rec=c.read(rp);j=req['job'];ck(rec['request_sha256']==c.sha(c.ROOT/a['request_path']),'receipt/request binding');ck(c.h(c.canonical(j['body']))==j['body_sha256'],'body SHA')
        tr=rec['transport'];n=json.loads(tr['body_text']) if tr['http_status']==200 else {};u=n.get('usage',{})
        value=(Decimal(u['prompt_tokens'])*3+Decimal(u['completion_tokens'])*9)/Decimal(1000000) if type(u.get('prompt_tokens'))is int and type(u.get('completion_tokens'))is int else Decimal(str(j['bound_cny']))
        ck(abs(float(value)-a['charge_cny'])<1e-10,'Decimal price');total+=value
    ck(total<=20,'whole task cap');ck(abs(float(total)-c.read(c.OUT/'cost_ledger.json')['original_price_or_reserved_cny'])<1e-9,'ledger total')
    inp={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};q={r['id']:r for r in c.lines(c.PRIVATE/'questions_reviewed.jsonl')};ext={(j['id'],j['arm']):j for j in c.lines(c.PRIVATE/'extract_jobs.jsonl')}
    for pid,qq in q.items():
        v=ext[pid,'V']['body'];b=ext[pid,'Q']['body'];vp=json.loads(v['messages'][1]['content']);bp=json.loads(b['messages'][1]['content'])
        ck(set(bp)=={'question','reference'},'Q input whitelist');ck(bp['reference']==inp[pid]['reference'],'Q fixed C48');ck(vp.pop('unverified_claim')==inp[pid]['text'] and vp==bp,'only visibility differs');ck(qq['answer_span'].lower() not in bp['question'].lower(),'withheld answer literal')
        for k in set(v)-{'messages'}:ck(v[k]==b[k],'matched extraction params')
    aligned={(r['id'],r['arm']):r for r in c.lines(c.PRIVATE/'extracted_aligned.jsonl')}
    for key,row in aligned.items():
        j=ext[key];p=grounding094.parse(s[j['request_id']]['tr'],inp[key[0]]['reference']);ck(p=={k:v for k,v in row.items() if k not in ['id','arm']},'deterministic grounding')
        for candidate in p['record']['candidates']:
            for e in candidate['evidence']:ck(e['quote'] in m.entries(inp[key[0]]['reference'])[e['reference_id']],'actual verbatim source')
    template=c.read(c.PRIVATE/'judge_template.json');byjob={j['request_id']:j for j in jobs};aliases=c.lines(c.OUT/'judge_aliases.jsonl')
    for a in aliases:
        j=byjob[a['request_id']];r=inp[a['id']];expected=m.judge_body(template,r) if a['arm']=='B' or not a['operated'] else m.judge_body(template,r,q[a['id']],aligned[a['id'],a['arm']]['record'])
        ck(j['body']==expected,'frozen final body or exact alias');ck(a['body_sha256']==j['body_sha256'],'alias SHA')
    rows=c.lines(c.OUT/'predictions_public.jsonl');analysis=c.read(c.OUT/'analysis.json');labels=['Supported','Not Supported','Not Addressed']
    for panel,d in analysis['panels'].items():
        rr=[r for r in rows if r['panel']==panel and all(r['arms'][a]['valid'] for a in ['B','V','Q'])]
        for method,metrics in d['metrics'].items():
            for arm,z in metrics.items():
                y=[r['GT'] for r in rr];p=[r['Original'] if arm=='Original' else r['labels'][arm][method] for r in rr]
                ck(confusion_matrix(y,p,labels=labels).tolist()==z['confusion_matrix'],'independent CM');ck(abs(accuracy_score(y,p)-z['PA'])<1e-10,'PA');ck(abs(matthews_corrcoef(y,p)-z['MCC'])<1e-10,'MCC');ck(abs(f1_score(y,p,labels=labels,average='macro',zero_division=0)-z['Macro_F1'])<1e-10,'MacroF1')
        for method,pairs in d['comparisons'].items():
            rrr=[r for r in rows if r['panel']==panel and all(r['arms'][a]['raw_valid' if method=='raw' else 'valid'] for a in ['B','V','Q'])]
            for pair,z in pairs.items():
                a,b=pair.split('-');rescue=sum(r['labels'][b][method]!=r['GT'] and r['labels'][a][method]==r['GT'] for r in rrr);harm=sum(r['labels'][b][method]==r['GT'] and r['labels'][a][method]!=r['GT'] for r in rrr)
                ck((rescue,harm,rescue-harm)==(z['rescue'],z['harm'],z['net']),'paired conservation')
    def privacy(v):
        if isinstance(v,dict):
            ck(not set(v)&{'text','claim','reference','body_text','reasoning_content','api_key','messages','quote','answer'},'no private payload fields')
            for x in v.values():privacy(x)
        elif isinstance(v,list):
            for x in v:privacy(x)
    for p in c.OUT.glob('*.json*'):
        if p.name=='preflight_result.json':continue # explicitly synthetic, public by design
        privacy(c.lines(p) if p.suffix=='.jsonl' else c.read(p))
    for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'));ck(True,'syntax '+p.name)
    ck(subprocess.run(['git','check-ignore','-q','.local_models/094/inputs.jsonl'],cwd=c.ROOT).returncode==0,'private directory ignored')
    paths=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True).splitlines();ck('.gitignore' not in paths,'gitignore unchanged');ck(not any(p.startswith(('tasks/','outputs/')) and '/094_answer_isolated_verification/' not in p for p in paths),'history unchanged')
    result=dict(status='PASS',checks=len(checks),cost_cny=str(total),completed_HTTP200=len(s),executor_selfcheck=True,independent_audit=False,utc=c.now())
    if (c.OUT/'selfcheck.json').exists():
        old=c.read(c.OUT/'selfcheck.json');ck(old['cost_cny']==result['cost_cny'] and old['completed_HTTP200']==len(s),'repeat verification agrees with preserved selfcheck')
    else:c.put(c.OUT/'selfcheck.json',result)
    print('Executor selfcheck PASS',len(checks),'cost',total)
if __name__=='__main__':main()
