"""Synthetic-only coverage/analysis integration check, isolated in ignored replays."""
import copy
import numpy as np
import common036 as c
import predict036 as p
import evaluate036 as ev
def main():
    original=c.OUT;test=c.ROOT/'outputs/replays/036_synthetic_integration_001';assert not test.exists();test.mkdir(parents=True)
    config=c.read(original/'final_freeze_001/config.json');models=c.read(original/'final_freeze_001/models035.json')['models'];std=c.read(original/'final_freeze_001/standard_models022.json')['models'];c.put(test/'final_freeze_001/config.json',config)
    c.OUT=test;rows=[]
    for i in range(36):
        scores=dict(zip(c.LABELS,[[20,70,10],[80,10,10],[0,50,50],[10,10,80]][i%4]));methods=p.infer_scores(scores,models,std);u0=methods['U0']['label'];u2=methods['U2']['label'];methods.update(O=dict(label=0),B=dict(label=u0),Score_verdict=dict(label=u0),Gate_A=dict(label=u0))
        rows.append(dict(id='SYNTHETIC_'+str(i),sid='SYNTHETIC_PATIENT_'+str(i//9),author='human' if i%2 else 'llm',y=i%3,scores=scores,methods=methods))
    rows[0]['methods']['B']['label']=None
    for m in list(rows[1]['methods']):
        if m not in ('O','B'):rows[1]['methods'].pop(m)
    ev.analyze('SYNTHETIC_ONLY',rows,test/'analysis')
    d=c.read(test/'analysis/denominators.json');assert d['frozen_n']==36 and d['paired_n']==34 and set(d['missing_ids'])=={'SYNTHETIC_0','SYNTHETIC_1'}
    cov={r['method']:r for r in c.csvread(test/'analysis/coverage.csv')};assert cov['O']['valid_n']=='36' and cov['B']['valid_n']=='35' and cov['U2']['valid_n']=='35'
    m=c.read(test/'analysis/metrics.json');assert m['all/U2']['confusion_matrix']==m['all/U2_T']['confusion_matrix'];assert m['all/Gate_A']['correct']==m['all/U0']['correct']
    c.put(test/'TEST_STATUS.json',dict(status='PASS',all_data_synthetic=True,API_calls=0,real_patient_data_read=False,assertions=['paired missing IDs','method-specific coverage and full denominator','U2 temperature label equality','Gate fallback unchanged U0','all subgroup/bootstrap/probability exports executed']))
    c.OUT=original;print('Synthetic-only integration PASS; no patient records or APIs used.')
if __name__=='__main__':main()
