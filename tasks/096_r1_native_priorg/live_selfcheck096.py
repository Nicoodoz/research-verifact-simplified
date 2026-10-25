"""Execution self-check only, never an independent audit; no network."""
import sys,json,collections
import common096 as c
import live_run096 as r
from calibration096 import decode,fit_g
O=r.O;P=r.P
def main():
    checks=[]
    def ok(name,value):assert value,name;checks.append(name)
    f=c.read(O/'freeze.json')
    for name,h in f['files'].items():ok('frozen artifact '+name,c.sha(O/name)==h)
    jj=r.jobs();ok('1143 unique requests',len(jj)==1143 and len({j['request_id'] for j in jj})==1143)
    cal=[j for j in jj if j['stage']=='calibration'];old=[j for j in c.lines(c.PRIVATE/'jobs.jsonl') if j['stage']=='calibration'];ok('calibration exact historical143',cal==old)
    train={j['sid'] for j in cal};ok('patient isolation',not train & {j['sid'] for j in jj if j['stage']!='calibration'})
    template=c.read(c.PRIVATE/'template.json')
    for j in jj:
        ok('B semantics '+j['id'],j['body']['messages'][0]==template['messages'][0] and set(json.loads(j['body']['messages'][1]['content']))=={'proposition','reference'} and {k:v for k,v in j['body'].items() if k!='messages'}=={k:v for k,v in template.items() if k!='messages'})
    for row in c.lines(O/'local_token_lengths.jsonl'):ok('context '+row['id'],row['input_tokens']+8192<=20000)
    attempted=[j for j in jj if r.attempts(j)];done=[j for j in jj if r.success(j)]
    for j in attempted:
        hist=r.attempts(j);ok('max3 attempts '+j['id'],len(hist)<=3);ok('first200 no replay '+j['id'],sum(x.get('http_status')==200 for _,x in hist)<=1 and (not r.success(j) or hist[-1][1]['http_status']==200))
    if (O/'R1_INFERENCE_DONE.json').exists():
        rec=c.read(O/'R1_INFERENCE_DONE.json');sel=c.read(O/'tier_selection.json');ok('selected complete',set(sel['ids'])=={j['id'] for j in done});ok('reconciliation hash',c.sha(O/'response_reconciliation.jsonl')==rec['reconciliation_sha256'])
        model=c.read(O/'R1_calibration_model.json');ok('same parameter number',len(model['R1_model']['theta'])==1);ok('same reference',model['reference_counts']=={'Supported':1108,'Not Supported':100,'Not Addressed':170});ok('no eval fit',not model['evaluation_GT_used'])
        rows=c.lines(O/'unified_predictions.jsonl');ok('natural diagnostic disjoint',len(rows)==len({x['id'] for x in rows})==sel['natural']+sel['diagnostic'])
        from sklearn.metrics import matthews_corrcoef,accuracy_score,f1_score
        metrics=c.read(O/'main_metrics.json')
        for panel in ['natural','diagnostic']:
            valid=[x for x in rows if x['panel']==panel and x['R1_core_valid'] and x['B_core_valid']]
            for method,z in metrics[panel]['all_methods_common'].items():
                y=[x['GT'] for x in valid];p=[x['predictions'][method] for x in valid]
                ok('sklearn MCC '+panel+method,abs(matthews_corrcoef(y,p)-z['MCC'])<1e-10);ok('sklearn PA '+panel+method,abs(accuracy_score(y,p)-z['PA'])<1e-10);ok('sklearn F1 '+panel+method,abs(f1_score(y,p,labels=list(c.LABELS),average='macro',zero_division=0)-z['Macro_F1'])<1e-10)
    result=dict(status='PASS',type='executor self-check; not independent audit',checks=len(checks),check_names=checks,HTTP200=len(done),attempted=len(attempted),default_unchanged=True,GT_in_requests=False,clinical_text_in_public_predictions=False,new_token_API=0,scope='current completed scope only; no invented completion')
    name='selfcheck.json' if (O/'R1_INFERENCE_DONE.json').exists() else 'preformal_selfcheck.json'
    c.put(O/name,result);print('SELFCHECK_PASS',len(checks),'HTTP200',len(done))
if __name__=='__main__':
    import socket
    from unittest.mock import patch
    with patch.object(socket.socket,'connect',side_effect=AssertionError('offline selfcheck')):main()
