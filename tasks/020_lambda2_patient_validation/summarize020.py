import json,csv,pathlib,collections
O=pathlib.Path(r'D:\Research-VeriFact\outputs\020_lambda2_patient_validation')
m=json.loads((O/'analysis_001/metrics.json').read_text(encoding='utf-8'))
p=json.loads((O/'analysis_001/paired.json').read_text(encoding='utf-8'))
d=json.loads((O/'analysis_001/decision.json').read_text(encoding='utf-8'))
s=json.loads((O/'live_ledger.json').read_text(encoding='utf-8'))
st=list(csv.DictReader((O/'analysis_001/stability.csv').open(encoding='utf-8-sig')))
pat=list(csv.DictReader((O/'analysis_001/patients.csv').open(encoding='utf-8-sig')))
tr=list(csv.DictReader((O/'analysis_001/transitions.csv').open(encoding='utf-8-sig')))
norm=[json.loads(x) for x in (O/'analysis_001/normalized.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
out={'attempts':sum(int(v['attempts']) for v in s['phases']['new10_judge']['jobs'].values()),
'extra_attempts':sum(max(0,int(v['attempts'])-1) for v in s['phases']['new10_judge']['jobs'].values()),
'cost':s['used_or_reserved_cny'],'provider':s.get('provider'),'exhausted':s.get('exhausted_accounts',[]),
'provider_counts':dict(collections.Counter(r['provider'] for r in norm)),'account_counts':dict(collections.Counter(r['account'] for r in norm)),
'stability':{k:sum(r[k]=='True' for r in st) for k in ['B_flip','V_raw_flip','U0_flip','U2_flip','stable_rescue','stable_harm']},
'rounds':{},'patient_net':{},'rhw':{}}
for rep in [0,1]:
    rr={}
    for a in ['all','llm','human']:
        aa={}
        for arm in ['B','V_raw','U0','U2','O','Always_S']:
            q=m[f'r{rep}/{a}/{arm}']; aa[arm]={'correct':q['counts']['correct'],'n':q['counts']['n'],'pa':q['percent_agreement'],'mcc':q['mcc'],'ac1':q['gwet_ac1'],'false_s':q['counts']['false_s'],'tp':q['counts']['tp']}
        rr[a]=aa
    out['rounds'][str(rep)]=rr
    out['patient_net'][str(rep)]=[]
    by={(r['subject_id'],r['arm']):int(r['correct']) for r in pat if r['repeat']==str(rep)}
    for sid in sorted({r['subject_id'] for r in pat if r['repeat']==str(rep)}):
        out['patient_net'][str(rep)].append({'subject_id':sid,'U2_minus_B':by[(sid,'U2')]-by[(sid,'B')],'U2_minus_O':by[(sid,'U2')]-by[(sid,'O')]})
    out['rhw'][str(rep)]=dict(collections.Counter(r['RHW'] for r in tr if r['repeat']==str(rep) and r['RHW']))
for rep in [0,1]:
    for base in ['B','U0','O']:
        z=p[f'r{rep}/all/U2-minus-{base}']['metrics']
        out.setdefault('paired',{})[f'r{rep}_U2_minus_{base}']={'dPA':z['percent_agreement']['delta'],'PA_CI':z['percent_agreement']['ci95'],'dMCC':z['mcc']['delta'],'MCC_CI':z['mcc']['ci95']}
out['decision']=d
print(json.dumps(out,ensure_ascii=False))
