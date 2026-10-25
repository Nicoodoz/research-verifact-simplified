import json,pathlib,hashlib
R=pathlib.Path(r'D:\Research-VeriFact')
d=json.loads((R/'outputs/020_lambda2_patient_validation/history_before.json').read_text(encoding='utf-8'))
ch=[];miss=[]
for n,h in d['files'].items():
    p=R/n
    if not p.is_file():
        miss.append(n);continue
    x=hashlib.sha256(p.read_bytes()).hexdigest()
    if x!=h:ch.append(n)
print('CHANGED',len(ch),ch[:50])
print('MISSING',len(miss),miss[:50])
