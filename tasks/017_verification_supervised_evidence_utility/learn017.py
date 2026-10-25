"""One preregistered pairwise linear utility ranker; only runs after headroom PASS."""
from pathlib import Path
import hashlib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import common017 as c
from io017 import logical

def fit(records,events,allowed_patients):
    byid={r['proposition_id']:r for r in records};xs=[];ys=[];provenance=[]
    for e in events:
        if e['subject_id'] not in allowed_patients or not int(e['utility']):continue
        item=byid[e['proposition_id']];action=item['interventions'][e['arm']]
        x=np.asarray(action['features_in'])-np.asarray(action['features_out']);target=int(e['utility'])>0
        c.require(x.shape==(len(c.FEATURES),) and np.isfinite(x).all(),'Only finite allowlisted features permitted')
        xs.extend([x,-x]);ys.extend([int(target),int(not target)])
        provenance.append(dict(proposition_id=e['proposition_id'],subject_id=e['subject_id'],arm=e['arm'],utility=int(e['utility'])))
    c.require(provenance,'No trainable utility pairs')
    x=np.asarray(xs);y=np.asarray(ys);scaler=StandardScaler().fit(x)
    model=LogisticRegression(C=.1,fit_intercept=False,solver='liblinear',random_state=17,max_iter=1000).fit(scaler.transform(x),y)
    return dict(features=list(c.FEATURES),scaler_mean=scaler.mean_.tolist(),scaler_scale=scaler.scale_.tolist(),coefficients=model.coef_[0].tolist(),
        fit_intercept=False,C=.1,solver='liblinear',random_state=17,max_iter=1000,training_patients=sorted(allowed_patients),
        original_pairs=len(provenance),symmetric_fit_rows=len(xs),X_sha256=hashlib.sha256(x.tobytes()).hexdigest(),y_sha256=hashlib.sha256(y.tobytes()).hexdigest()),provenance

def choose(item,model,wide):
    scores={};best='baseline';margin=0.
    for arm in c.SWAPS if wide else c.SWAPS[:2]:
        r=item['interventions'][arm]
        if not r['eligible']:continue
        x=np.asarray(r['features_in'])-np.asarray(r['features_out'])
        score=float(((x-np.asarray(model['scaler_mean']))/np.asarray(model['scaler_scale']))@np.asarray(model['coefficients']))
        scores[arm]=score
        if score>margin:best=arm;margin=score
    return best,margin,scores

def selection_gate(cohort,preds,metrics,repeat):
    truth={r['proposition_id']:r['human_gt'] for r in cohort}
    def correct(method,rows=cohort):return sum(preds[method][r['proposition_id']]==r['human_gt'] for r in rows)
    result={}
    for method in ('utility_C48','utility_W'):
        checks={'net_vs_C48':correct(method)-correct('baseline')>=8,'net_vs_W_relevance':correct(method)-correct('wide_relevance')>=5}
        for author in ('llm','human'):
            own=[r for r in cohort if r['author_type']==author]
            checks[author+'_net']=correct(method,own)-correct('baseline',own)>=2
            if repeat==0:
                m=metrics[author];checks[author+'_MCC']=m[method]['mcc']-m['baseline']['mcc']>=.03
                checks[author+'_AC1']=m[method]['gwet_ac1']>=m['baseline']['gwet_ac1']
                checks[author+'_false_S']=m[method]['per_class']['Supported']['fp']<=m['baseline']['per_class']['Supported']['fp']+1
                for label in c.LABELS:checks[author+'_'+label]=m[method]['per_class'][label]['tp']>=m['baseline']['per_class'][label]['tp']-1
        deltas={sid:correct(method,[r for r in cohort if r['subject_id']==sid])-correct('baseline',[r for r in cohort if r['subject_id']==sid]) for sid in {r['subject_id'] for r in cohort}}
        if repeat==0:checks['patients_positive']=sum(v>0 for v in deltas.values())>=4;checks['patient_harm']=min(deltas.values())>=-2
        result[method]=dict(passed=all(checks.values()),conditions=checks,net=correct(method)-correct('baseline'),patient_net=deltas)
    return result

def learn(out):
    c.require(c.read(c.OUT/'analysis_001/gate.json')['passed'],'Headroom failed: selector training forbidden')
    c.require(not out.exists(),'Learning result exists');c.check(c.OUT/'analysis_001')
    rows=c.jsonlines(c.OUT/'preparation_001/inputs.jsonl');events=c.csvrows(c.OUT/'analysis_001/utility_events.csv');split=c.read(c.OUT/'preparation_001/sampling.json')
    train=set(split['train_patients']);selection=set(split['selection_patients']);c.require(not train&selection,'Patient leakage')
    model,provenance=fit(rows,events,train)
    c.require(all(p['subject_id'] in train and p['subject_id'] not in selection for p in provenance),'Fit leakage')
    _,_,_,_,labels,_,_=logical();cohort=[r for r in c.csvrows(c.OUT/'evaluation_cohort.csv') if r['subject_id'] in selection]
    actions=[];mapping={}
    for r in rows:
        for method,wide in [('utility_C48',False),('utility_W',True)]:
            arm,margin,scores=choose(r,model,wide);mapping[(r['proposition_id'],method)]=arm
            actions.append(dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],split=r['split'],method=method,selected_arm=arm,margin=margin,all_margins=c.canonical(scores)))
    out.mkdir(parents=True);c.write_json(out/'model.json',model);c.write_csv(out/'training_pairs.csv',provenance);c.write_csv(out/'actions.csv',actions)
    metrics={};paired={};gates={};summary=[]
    for repeat in (0,1):
        preds={method:{r['proposition_id']:labels[(r['proposition_id'],mapping[(r['proposition_id'],method)] if method.startswith('utility_') else method,repeat)] for r in cohort}
            for method in ('baseline','wide_relevance','utility_C48','utility_W')}
        metrics[str(repeat)]={};paired[str(repeat)]={}
        for author in ('llm','human'):
            own=[r for r in cohort if r['author_type']==author];ids={r['proposition_id'] for r in own}
            p={m:[dict(proposition_id=pid,verdict=v) for pid,v in pp.items() if pid in ids] for m,pp in preds.items()}
            mm={m:c.evaluate(own,v,iterations=1000,missing='error') for m,v in p.items()};metrics[str(repeat)][author]=mm
            paired[str(repeat)][author]={m:c.paired_compare(own,p['baseline'],v,iterations=1000) for m,v in p.items() if m!='baseline'}
            for m,v in mm.items():summary.append(dict(repeat=repeat,author=author,method=m,correct=sum(v['confusion_matrix'][i][i] for i in range(3)),n=v['n'],PA=v['percent_agreement'],AC1=v['gwet_ac1'],MCC=v['mcc']))
        gates[str(repeat)]=selection_gate(cohort,preds,metrics[str(repeat)],repeat)
        for method,pp in preds.items():c.write_csv(out/f'predictions_r{repeat}_{method}.csv',[dict(proposition_id=pid,verdict=v) for pid,v in pp.items()])
    winners=[m for m in ('utility_C48','utility_W') if all(gates[str(r)][m]['passed'] for r in (0,1))]
    winner=max(winners,key=lambda m:(gates['0'][m]['net'],m=='utility_C48')) if winners else None
    for name,data in [('metrics',metrics),('paired',paired),('gates',gates)]:c.write_json(out/(name+'.json'),data)
    c.write_csv(out/'results.csv',summary)
    c.write_json(out/'summary.json',dict(train_patients=sorted(train),selection_patients=sorted(selection),selection_claims=len(cohort),patient_disjoint=True,
        winner=winner,passed=bool(winner),new_API_calls=0,from_exhaustive_GT_blind_logged_actions=True,hyperparameter_search=False))
    c.seal(out,[c.OUT/'analysis_001/manifest.json',c.OUT/'preparation_001/manifest.json'],[Path(__file__),c.TASK/'selection017.py'])
    print(c.canonical(c.read(out/'summary.json')))

if __name__=='__main__':learn(c.OUT/'learning_001')
