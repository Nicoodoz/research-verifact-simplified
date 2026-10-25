"""Read-only targeted eligible-EHR discovery, not candidate retrieval or evaluation input."""
import gzip,csv,re
import common095 as c
TARGETS={14:r'bolus|1\s*l|1000|liter',29:r'oral|\bpo\b|pain|regimen',11:r'nod|question',19:r'renal|nephrol|consult'}
def main():
    raw=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr';rows=[r for r in c.lines(c.PRIVATE/'diagnosis_cases.jsonl') if r['review_owner']=='root'];selected={rows[i]['id']:(rows[i],re.compile(p,re.I)) for i,p in TARGETS.items()}
    with gzip.open(raw/'admissions.csv.gz','rt',encoding='utf-8',newline='') as f:ad={str(int(r['SUBJECT_ID'])):r for r in csv.DictReader(f)}
    candidates={pid:[] for pid in selected}
    with gzip.open(raw/'ehr_noteevents.csv.gz','rt',encoding='utf-8',newline='') as f:
        for n in csv.DictReader(f):
            sid=str(int(n['SUBJECT_ID']));date=n['CHARTDATE'][:10]
            if sid not in {r['sid'] for r,_ in selected.values()} or n['CATEGORY'].strip().lower()=='discharge summary' or not ad[sid]['ADMITTIME'][:10]<=date<=ad[sid]['DISCHTIME'][:10]:continue
            for pid,(r,pat) in selected.items():
                if r['sid']!=sid:continue
                for match in pat.finditer(n['TEXT']):
                    lo=max(0,match.start()-160);hi=min(len(n['TEXT']),match.end()+280);text=n['TEXT'][lo:hi]
                    if text in r['reference']:continue
                    terms=len(set(re.findall(r'[a-z]{3,}',r['claim'].lower()))&set(re.findall(r'[a-z]{3,}',text.lower())))
                    if terms<2:continue
                    candidates[pid].append(dict(note_id=n['ROW_ID'],date=date,category=n['CATEGORY'],start=lo,end=hi,text=text,overlap=terms))
    out=[]
    for pid,ss in candidates.items():
        r=selected[pid][0];ss=sorted(ss,key=lambda x:(-x['overlap'],x['date'],x['note_id'],x['start']));seen=set();kept=[]
        for x in ss:
            if (x['note_id'],x['start']//300) in seen:continue
            seen.add((x['note_id'],x['start']//300));kept.append(x)
            if len(kept)==6:break
        out.append(dict(id=pid,candidates=kept));print('ID',pid,'CLAIM',r['claim'])
        for x in kept:print(x)
    c.putl(c.PRIVATE/'outside_discovery.jsonl',out)
if __name__=='__main__':main()
