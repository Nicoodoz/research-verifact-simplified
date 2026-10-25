"""Descriptive subgroup, cost and paired transition tables; no method selection."""
from collections import Counter
import platform,sys,importlib.metadata
import numpy as np
import common026 as c

def run():
    a=c.OUT/'analysis_001';out=c.OUT/'supplement_001';out.mkdir(exist_ok=False)
    jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);preds=c.csvread(a/'predictions.csv');metrics=c.read(a/'metrics.json');curves=c.csvread(a/'global_frontier.csv');summ={}
    for author in ('all','human','llm'):
        rows=[r for r in preds if author=='all' or r['author_type']==author];cc=[r for r in curves if r['scope']=='primary_common' and r['author']==author]
        risk=np.array([float(r['risk']) for r in cc]);rescue=np.array([float(r['R']) for r in cc]);summ[author]={}
        for name in ('SD','peer_U2'):
            m=metrics[author+'/'+name];summ[author][name]=c.frontier.matched(risk,rescue,m['risk'],m['R'])
        summ[author]['GT']=dict(Counter(r['GT'] for r in rows));summ[author]['always_S_PA']=sum(r['GT']=='Supported' for r in rows)/len(rows)
        summ[author]['paired_transitions']={}
        for cand,base in [('SD','U0'),('SD','U2'),('SD','B'),('peer_U2','U2')]:
            summ[author]['paired_transitions'][cand+'-minus-'+base]=dict(wrong_to_right=sum(r[cand]==r['GT'] and r[base]!=r['GT'] for r in rows),right_to_wrong=sum(r[cand]!=r['GT'] and r[base]==r['GT'] for r in rows),labels_changed=sum(r[cand]!=r[base] for r in rows))
    by_arm={arm:sum(a['charge_cny'] for a in attempts if a['model_key']+'_'+a['arm']==arm) for arm in ('deepseek_B','deepseek_S','qwen_S')}
    c.put(out/'descriptive.json',dict(subgroups=summ,cost_by_arm=by_arm,conditional_inference_cost=by_arm['deepseek_S']+by_arm['qwen_S'],qwen_increment_over_D_scoring=by_arm['qwen_S']/by_arm['deepseek_S'],requests=1352,candidates=52,parse_status=dict(Counter(v['status'] for v in term.values()))))
    c.put(out/'environment.json',dict(python=sys.version,platform=platform.platform(),packages={k:importlib.metadata.version(k) for k in ('numpy','scipy','scikit-learn','pandas')}))
    c.put(out/'manifest.json',dict(sha256={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.TASK/'supplement026.py',a/'manifest.json',out/'descriptive.json',out/'environment.json']}))
    print(c.canonical(c.read(out/'descriptive.json')))
if __name__=='__main__':run()
