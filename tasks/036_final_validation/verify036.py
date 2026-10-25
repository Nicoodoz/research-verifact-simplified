"""Safe offline replay of fixed parameters, predictions, metrics and raw receipts."""
import argparse,sys
from pathlib import Path
import numpy as np
import common036 as c
import api036 as api
import predict036 as pred
import evaluate036 as ev
def main(output):
    out=Path(output).resolve();assert out.is_relative_to(c.ROOT/'outputs/replays') and not out.exists()
    checks={}
    def check(k,v):assert v,k;checks[k]=True
    for name,h in c.read(c.OUT/'published_baseline_sources_001.json')['sha256'].items():check('published_input_'+name,c.sha(c.ROOT/name)==h)
    for path in [c.OUT/'final_freeze_001',c.OUT/'evaluation_freeze_001']:
        m=c.read(path/'manifest.json')
        for name,h in m.get('files',{}).items():check('frozen_'+path.name+'/'+name,c.sha(path/name)==h)
        for name,h in m.get('sha256',{}).items():check('code_'+name,c.sha(c.ROOT/name)==h)
    d=c.OUT/'development_001';m=c.read(d/'manifest.json')
    for name,h in m['sources'].items():check('historical_'+name,c.sha(c.ROOT/name)==h)
    for name,h in m['files'].items():check('dev_'+name,c.sha(d/name)==h)
    f=c.OUT/'final_freeze_001';models=c.read(f/'models035.json')['models'];std=c.read(f/'standard_models022.json')['models'];gate=c.read(f/'gate_A.json')
    blinded=c.lines(c.OUT/'predictions_blind_001/predictions.jsonl');by={(r['round'],r['id']):r for r in blinded}
    check('prediction_keys_unique',len(by)==len(blinded));cfg=c.read(f/'config.json')
    check('reserved_exact40',{r['sid'] for r in blinded if r['round']=='R0'}==set(cfg['patient_ids']))
    check('repeat_exact4',{r['sid'] for r in blinded if r['round']=='R1'}==set(cfg['repeat_patients']))
    for r in blinded:
        check('no_GT_'+r['round']+r['id'],'y' not in r and 'human_gt' not in r)
        if r['status']['score'] not in api.api.VALID:
            check('invalid_score_not_used_'+r['round']+r['id'],'U0' not in r['methods'] and not r['candidate'] and r['features'] is None)
            continue
        inferred=pred.infer_scores(r['scores'],models,std)
        for name,value in inferred.items():
            check('label_'+r['round']+r['id']+name,value['label']==r['methods'][name]['label']);np.testing.assert_allclose(value['logprob'],r['methods'][name]['logprob'],atol=1e-12,rtol=0)
        u0=r['methods']['U0']['label'];u2=r['methods']['U2']['label'];check('candidate_'+r['round']+r['id'],r['candidate']==(u0!=0 and u2==0))
        if r['features']:
            features=c.base.score_features(r['scores'],r['peer_scores']);check('raw_gate_features_'+r['round']+r['id'],features==r['features']);g=pred.gate(gate,features);check('gate_'+r['round']+r['id'],g==r['gate'] and r['methods']['Gate_A']['label']==(0 if g['keep'] else u0))
        else:check('gate_fallback_'+r['round']+r['id'],r['methods']['Gate_A']['label']==u0)
    sealed=c.read(c.OUT/'predictions_blind_001/manifest.json');joined=c.read(c.OUT/'analysis_001/GT_join.json');check('GT_join_after_predictions',sealed['created_utc']<joined['created_utc'])
    for rn in ('R0','R1','R0_repeat_subset'):
        folder=c.OUT/'analysis_001'/rn
        if not folder.exists():continue
        rows=c.csvread(folder/'predictions.csv');rr=[dict(id=r['id'],sid=r['sid'],author=r['author'],y=c.LABELS.index(r['GT'])) for r in rows];metrics=c.read(folder/'metrics.json')
        for scope in ('all','human','llm'):
            ii=[i for i,r in enumerate(rr) if scope=='all' or r['author']==scope];ss=[rr[i] for i in ii]
            for method in cfg['methods']:
                p=np.array([c.LABELS.index(rows[i][method]) for i in ii]);v=ev.point(ss,p);expected=metrics[scope+'/'+method]
                for key in ('n','correct','PA','MCC','AC1','false_S','confusion_matrix','S_recall','NS_recall','NA_recall'):check('metric_'+rn+scope+method+key,v[key]==expected[key])
        risk={r['method']:r for r in c.csvread(folder/'risk_rescue.csv') if r['scope']=='all'};u=risk['U2'];g=risk['Gate_A'];mm=lambda name:metrics['all/'+name]
        check('U2_error_transfer_'+rn,int(u['R'])-int(u['H'])==mm('U2')['correct']-mm('U0')['correct'])
        check('U2_new_falseS_'+rn,int(u['H'])+int(u['W'])==mm('U2')['false_S']-mm('U0')['false_S'])
        check('Gate_error_transfer_'+rn,int(u['H'])-int(g['H'])-int(u['R'])+int(g['R'])==mm('Gate_A')['correct']-mm('U2')['correct'])
        pairs=c.read(folder/'paired.json')
        for new,base in cfg['primary_pairs']:
            p=[dict(proposition_id=r['id'],verdict=r[new]) for r in rows];b=[dict(proposition_id=r['id'],verdict=r[base]) for r in rows];v=ev.old.paired_compare(ev.old.cohort(rr),b,p,iterations=1000)
            check('bootstrap_'+rn+new+base,v['metrics']==pairs['all/'+new+'-vs-'+base]['metrics'])
    attempts,terminal,_=api.state();check('cost_within150',sum(x['charge_cny'] for x in attempts)<=150);check('immutable_HTTP200_unique',len(terminal)==sum(x['http_status']==200 for x in attempts))
    c.put(out/'verification.json',dict(created_utc=c.now(),status='EXECUTOR_SELF_CHECK_PASS',independent_audit='pending',checks_n=len(checks),checks=checks,API_calls=0,raw_attempts_checked=len(attempts)))
    print('036 offline self-check PASS',len(checks),'checks; independent audit pending')
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);main(parser.parse_args().output)
