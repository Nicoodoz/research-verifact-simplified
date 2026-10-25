"""Fixed lambda020 evaluation; reads labels only after all Judge answers are sealed."""
from pathlib import Path
from collections import Counter
import csv,json
import duckdb,numpy as np,pandas as pd
import common020 as c
from io020 import load_phase

def run():
    c.require(not (c.OUT/'task_api.lock').exists(),'API still active')
    values,attempts=load_phase('new10_judge')
    c.require(all(v['status']=='received' for v in values.values()),'Incomplete/invalid answers; no available-case scoring')
    prep=c.OUT/'new10/base_preparation_001';cp=c.OUT/'new10/preparation_002/cohort.csv'
    c.check_manifest(cp.parent);rows=c.csvrows(cp);c.require(len(rows)==879,'Expected879')
    assign=c.csvrows(prep/'assignments.csv');logical={(r['proposition_id'],r['arm'],int(r['repeat'])):values[r['request_id']] for r in assign}
    c.require(len(logical)==3516,'Complete logical factorial required')
    release=c.RAW/'verifact/verdicts.parquet';man=c.read(c.ROOT/'outputs/002_reproduce_paper_results/run_003/manifest.json')
    c.require(c.file_hash(release)==man['input_sha256'][release.relative_to(c.RAW).as_posix()],'Release changed')
    with duckdb.connect() as db:
        db.register('wanted',pd.DataFrame({'proposition_id':[r['proposition_id'] for r in rows]}))
        original=db.execute('SELECT v.proposition_id,v.verdict,v.model,v.reference_id FROM read_parquet(?) v JOIN wanted USING(proposition_id) WHERE rater_alias=?',[str(release),'v1.1.0-rater-121']).fetchdf().to_dict('records')
    c.require(len(original)==879 and all(r['model']=='R1-70B' for r in original),'Original full comparison unavailable')
    O={r['proposition_id']:r['verdict'] for r in original};out=c.OUT/'analysis_001';out.mkdir(exist_ok=False)
    c.write_csv(out/'released_predictions.csv',original)
    normalized=[dict(request_id=rid,arm=v['job']['arm'],repeat=v['job']['repeat'],provider=v['receipt']['provider'],account=v['receipt']['account'],**v['parsed']) for rid,v in values.items()]
    c.write_lines(out/'normalized.jsonl',normalized)
    metrics={};paired={};patients=[];changes=[];repeats={};rates=[]
    for rep in range(2):
        b=[logical[(r['proposition_id'],'B',rep)]['parsed'] for r in rows]
        s=[logical[(r['proposition_id'],'S',rep)]['parsed'] for r in rows]
        preds={'B':[v['verdict'] for v in b],'V_raw':[v['verdict'] for v in s],'U0':[c.decision(v['scores'],0) for v in s],
            'U2':[c.decision(v['scores'],2) for v in s],'O':[O[r['proposition_id']] for r in rows],'Always_S':['Supported']*len(rows)}
        repeats[rep]=preds
        c.write_csv(out/f'predictions_r{rep}.csv',[dict(proposition_id=r['proposition_id'],subject_id=r['subject_id'],author_type=r['author_type'],human_gt=r['human_gt'],**{a:p[i] for a,p in preds.items()}) for i,r in enumerate(rows)])
        for author in ('all','llm','human'):
            ix=[i for i,r in enumerate(rows) if author=='all' or r['author_type']==author];rr=[rows[i] for i in ix]
            for arm,pred in preds.items():
                key=f'r{rep}/{author}/{arm}';pv=[pred[i] for i in ix]
                metrics[key]=c.evaluate(rr,c.prediction_rows(rr,pv));metrics[key]['counts']=c.totals(rr,pv)
            for cand,base in [('U2','B'),('U2','U0'),('U2','O'),('V_raw','B'),('U0','V_raw')]:
                paired[f'r{rep}/{author}/{cand}-minus-{base}']=c.paired_compare(rr,c.prediction_rows(rr,[preds[base][i] for i in ix]),c.prediction_rows(rr,[preds[cand][i] for i in ix]))
        for sid in sorted({r['subject_id'] for r in rows}):
            for arm,p in preds.items():
                ix=[i for i,r in enumerate(rows) if r['subject_id']==sid]
                patients.append(dict(repeat=rep,subject_id=sid,arm=arm,**c.totals([rows[i] for i in ix],[p[i] for i in ix])))
        for i,r in enumerate(rows):
            g=r['human_gt'];u0=preds['U0'][i];u2=preds['U2'][i]
            rhw='R' if u0!='Supported' and u2=='Supported' and g=='Supported' else 'H' if u0==g!='Supported' and u2=='Supported' else 'W' if g!='Supported' and u0 not in (g,'Supported') and u2=='Supported' else ''
            changes.append(dict(repeat=rep,proposition_id=r['proposition_id'],author_type=r['author_type'],GT=g,B=preds['B'][i],V_raw=preds['V_raw'][i],U0=u0,U2=u2,RHW=rhw,raw_final_mismatch=preds['V_raw'][i]!=u2))
    c.write_json(out/'metrics.json',metrics);c.write_json(out/'paired.json',paired)
    c.write_csv(out/'patients.csv',patients);c.write_csv(out/'transitions.csv',changes)
    stability=[]
    for i,r in enumerate(rows):
        providers={logical[(r['proposition_id'],arm,t)]['receipt']['provider'] for arm in ('B','S') for t in range(2)}
        stability.append(dict(proposition_id=r['proposition_id'],author_type=r['author_type'],same_provider=len(providers)==1,
            **{arm+'_flip':repeats[0][arm][i]!=repeats[1][arm][i] for arm in ('B','V_raw','U0','U2')},
            stable_rescue=all(repeats[t]['B'][i]!=r['human_gt']==repeats[t]['U2'][i] for t in range(2)),
            stable_harm=all(repeats[t]['B'][i]==r['human_gt']!=repeats[t]['U2'][i] for t in range(2))))
    c.write_csv(out/'stability.csv',stability)
    leave=[]
    for rep in range(2):
        for sid in sorted({r['subject_id'] for r in rows}):
            ix=[i for i,r in enumerate(rows) if r['subject_id']!=sid];rr=[rows[i] for i in ix]
            m={a:c.evaluate(rr,c.prediction_rows(rr,[repeats[rep][a][i] for i in ix]),profile='none') for a in ('B','U0','U2','O')}
            leave.append(dict(repeat=rep,excluded_patient=sid,**{a+'_'+k:m[a][k] for a in m for k in ('percent_agreement','mcc')}))
    c.write_csv(out/'leave_one_patient_out.csv',leave)
    outcome={}
    for author in ('all','llm','human'):
        outcome[author]={}
        for base in ('B','U0','O'):
            v=[paired[f'r{rep}/{author}/U2-minus-{base}']['metrics'] for rep in range(2)]
            outcome[author][base]=dict(two_round_PA_positive=all(x['percent_agreement']['delta']>0 for x in v),
                two_round_MCC_positive=all(x['mcc']['delta']>0 for x in v),
                joint_positive=all(x[k]['delta']>0 for x in v for k in ('percent_agreement','mcc')),
                all_CI_lower_positive=all(x[k]['ci95'][0]>0 for x in v for k in ('percent_agreement','mcc')))
    c.write_json(out/'decision.json',dict(fixed_lambda=2,claims=879,rounds=2,primary_scope='all micro',outcome=outcome,
        reserved_test_used=False,core_replaced=False,independent_audit=False,protocol_changed_after_results=False))
    c.seal(out,[cp,prep/'manifest.json',c.OUT/'protocol_001.md',release],[Path(__file__),c.TASK/'common020.py',c.TASK/'io020.py'])
    print(c.canonical(outcome),flush=True)

if __name__=='__main__':run()
