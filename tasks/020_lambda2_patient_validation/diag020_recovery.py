import json,pathlib,hashlib
R=pathlib.Path(r'D:\Research-VeriFact'); O=R/'outputs/020_lambda2_patient_validation'
A=json.loads((O/'authority.json').read_text(encoding='utf-8'))
bad=[]
for n,h in A['sha256'].items():
    p=R/n
    x=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
    if x!=h: bad.append((n,h,x))
print('AUTH_BAD',len(bad),bad[:10])
jobs=[json.loads(x) for x in (O/'new10/base_preparation_001/jobs.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
rid='020:new10:r1:29093318242fb4bb60c993795bc9feed7c28f5c6e77d56f2db6bb36dd6693d05'
j=next(x for x in jobs if x['request_id']==rid)
enc=json.dumps(j['body'],ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
print('FAIL_JOB',{'kind':j['kind'],'arm':j['arm'],'repeat':j['repeat'],'bytes':len(enc),'message_count':len(j['body']['messages']),'model':j['body']['model'],'max_tokens':j['body']['max_tokens'],'json_roundtrip':json.loads(enc.decode('utf-8'))==j['body']})
sizes=sorted(len(json.dumps(x['body'],ensure_ascii=False,separators=(',',':')).encode('utf-8')) for x in jobs)
print('SIZE_DIST',{'min':sizes[0],'median':sizes[len(sizes)//2],'p99':sizes[int(.99*(len(sizes)-1))],'max':sizes[-1]})
