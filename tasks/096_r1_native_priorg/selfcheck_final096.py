"""Offline executor review: native receipt replay, source/GT alignment, math checks."""
import sys,json,math,collections,subprocess,socket
from unittest.mock import patch
import numpy as np
import common096 as c
import marlin096 as m
from live_prepare096 import sample
from calibration096 import decode,z_from_scores,obj_grad_hess
from sklearn.metrics import accuracy_score,matthews_corrcoef,f1_score
sys.path.insert(0,str(c.ROOT/'src'))
from verifact_research.evaluation import paired_compare
O=m.O
def main():
    m.activate();checks=[]
    def ok(name,b):assert b,name;checks.append(name)
    old=c.lines(m.OLD_P/'jobs.jsonl');jobs=m.r.jobs();pub={x['id']:x for x in c.lines(O/'R1_parsed_predictions.jsonl')};rows=c.lines(O/'unified_predictions.jsonl');model=c.read(O/'R1_calibration_model.json')
    ok('unique requests',len(jobs)==len({j['id'] for j in jobs})==len({j['request_id'] for j in jobs})==1143)
    for a,b in zip(old,jobs):
        ok('unchanged body '+b['id'],a['id']==b['id'] and a['body']==b['body'] and a['request_id']!=b['request_id'])
        ok('no GT request '+b['id'],set(json.loads(b['body']['messages'][1]['content']))=={'proposition','reference'})
        hist=m.r.attempts(b);ok('unique HTTP200 '+b['id'],len(hist)==1 and hist[0][1]['http_status']==200 and hist[0][1]['backend_id']==m.BACKEND)
        p=m.r.parsed(b);x=pub[b['id']];ok('native replay '+b['id'],p['verdict']==x['verdict'] and p['label_scores']==x['label_scores'] and p['valid']==x['raw_valid'])
    for name,h in c.read(m.OLD_O/'freeze.json')['files'].items():
        ok('old freeze '+name,c.sha(m.OLD_O/name)==h)
        if name!='request_manifest.jsonl':ok('sample unchanged '+name,c.sha(O/name)==h)
    ledger=c.lines(O/'candidate_ledger.jsonl');pool=[r for r in ledger if r['exclusion_reason'] is None];ok('eligible size',len(pool)==7484)
    for n in [400,600,800]:ok('sample replay '+str(n),sample(pool,n,'096/live/natural/v1/')==c.lines(O/f'natural{n}.jsonl'))
    mainids={r['id'] for r in c.lines(O/'natural800.jsonl')};diag=c.lines(O/'diagnostic200.jsonl');expected=sum([sample([r for r in pool if r['GT']==lab and r['id'] not in mainids],100,'096/live/diagnostic/v1/') for lab in c.LABELS[1:]],[]);ok('diagnostic replay',expected==diag)
    train=[j for j in jobs if j['stage']=='calibration'];ok('143 and16',len(train)==143 and len({j['sid'] for j in train})==16);ok('patient disjoint',not {j['sid'] for j in train}&{r['sid'] for r in rows})
    old085={j['id'] for j in c.lines(c.ROOT/'.local_models/085_valdemardi_private/jobs.jsonl')};ok('085 excluded',not old085&{r['id'] for r in rows})
    truth={r['id']:r for r in c.lines(c.PRIVATE/'calibration_supervision.jsonl')};good=[r for r in pub.values() if r['stage']=='calibration' and r['core_valid']];ok('calibration intersection142',len(good)==142 and sorted(r['id'] for r in good)==model['calibration_ids'])
    ok('calibration counts',dict(collections.Counter(truth[r['id']]['GT'] for r in good))==model['counts']=={'Supported':48,'Not Supported':46,'Not Addressed':48})
    ok('prior reference unchanged',model['reference_counts']=={'Supported':1108,'Not Supported':100,'Not Addressed':170})
    theta=model['R1_model']['theta'][0];z=z_from_scores([r['label_scores'] for r in good]);y=np.array([c.LABELS.index(truth[r['id']]['GT']) for r in good]);loss,g,h=obj_grad_hess([theta],z,y,'G')
    ok('bound KKT without changing solver theta',theta==-6 and g[0]>0 and h[0,0]>0 and model['R1_model']['success'] is False and model['R1_model']['constrained_optimum_verified'])
    ok('bound objective exact',abs(loss-model['R1_model']['objective'])<1e-12)
    # Independently decode using explicit arithmetic and stable tie preference.
    def manual(s,t=0,counts=None):
        vals={k:math.log(max(s[k]/100,1e-6))+(t if k=='Supported' else 0) for k in c.LABELS}
        if counts:
            ref=model['reference_counts'];vals={k:v+math.log((ref[k]/sum(ref.values()))/(counts[k]/sum(counts.values()))) for k,v in vals.items()}
        return max(['Not Supported','Not Addressed','Supported'],key=lambda k:vals[k])
    base={r['id']:r for r in c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl')}
    for r in rows:
        b=base[r['id']];ok('baseline and GT '+r['id'],r['GT']==b['GT'] and r['sid']==b['sid'] and r['predictions']['Original']==b['predictions']['Original'] and r['predictions']['V4_raw']==b['predictions']['B_raw'])
        s=r['R1_scores'];p=r['predictions'];preds=dict(R1_U0=manual(s),R1_G_only=manual(s,theta),R1_prior_only=manual(s,0,model['counts']),R1_V4_PriorG=manual(s,model['old_V4_theta'],model['old_counts']),R1_adapted_PriorG=manual(s,theta,model['counts']))
        ok('independent decode '+r['id'],all(p[k]==v for k,v in preds.items()))
        if r['B_core_valid']:ok('V4 prior replay '+r['id'],p['V4_PriorG']==manual(r['V4_scores'],model['old_V4_theta'],model['old_counts']))
    mm=c.read(O/'main_metrics.json');pp=c.read(O/'paired_bootstrap.json')
    for panel in ['natural','diagnostic']:
        rr=[r for r in rows if r['panel']==panel]
        for scope,tt in [('raw_common',mm[panel]['raw_common']),('all_methods_common',mm[panel]['all_methods_common'])]:
            valid=rr if scope=='raw_common' else [r for r in rr if r['B_core_valid'] and r['R1_core_valid']]
            for method,v in tt.items():
                gt=[r['GT'] for r in valid];pred=[r['predictions'][method] for r in valid]
                ok('sklearn PA/MCC/F1 '+panel+scope+method,abs(accuracy_score(gt,pred)-v['PA'])<1e-12 and abs(matthews_corrcoef(gt,pred)-v['MCC'])<1e-12 and abs(f1_score(gt,pred,labels=list(c.LABELS),average='macro',zero_division=0)-v['Macro_F1'])<1e-12)
        for name,v in pp[panel].items():
            a=v['base'];b=v['candidate'];valid=[r for r in rr if r['predictions'].get(a) in c.LABELS and r['predictions'].get(b) in c.LABELS]
            rescue=sum(r['predictions'][a]!=r['GT'] and r['predictions'][b]==r['GT'] for r in valid);harm=sum(r['predictions'][a]==r['GT'] and r['predictions'][b]!=r['GT'] for r in valid)
            ok('pair transition '+panel+name,rescue==v['rescue'] and harm==v['harm'] and len(valid)==v['N'])
        a='V4_raw';b='R1_raw';replay=paired_compare([dict(proposition_id=r['id'],subject_id=r['sid'],human_gt=r['GT']) for r in rr],[dict(proposition_id=r['id'],verdict=r['predictions'][a]) for r in rr],[dict(proposition_id=r['id'],verdict=r['predictions'][b]) for r in rr],iterations=1000)
        ok('bootstrap replay '+panel,replay==pp[panel]['R1_raw_vs_V4_raw']['official_paired_compare'])
    ok('no new runtime attempts',sum(len(m.r.attempts(j)) for j in jobs)==1143)
    status=subprocess.check_output(['git','diff','--name-only'],cwd=c.ROOT,text=True);ok('historical/default files untouched',not any(x.startswith(('tasks/085','outputs/085','tasks/095','outputs/095','src/')) or x=='.gitignore' for x in status.splitlines()))
    c.put(O/'selfcheck.json',dict(status='PASS',type='executor self-check, not independent audit',checks=len(checks),check_names=checks,network_blocked=True,GT_not_in_inference=True,old_AWQ_excluded=True,historical_files_unchanged=True,scope='native source/hash replay, deterministic sampling, fixed calibration/KKT, independent label arithmetic, sklearn metrics and patient bootstrap replay',code_sha256={p.name:c.sha(p) for p in c.TASK.glob('*.py')}))
    print('FINAL_SELFCHECK_PASS',len(checks))
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('offline final selfcheck')):main()
