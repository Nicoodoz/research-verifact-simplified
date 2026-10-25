import common092 as c
def main():
    rows=c.lines(c.OUT/'cohort.jsonl');master={r['proposition_id']:r for r in c.csvrows(c.ROOT/'outputs/002_reproduce_paper_results/run_003/cohort_master.csv')}
    for r in rows:
        r.update({k:master[r['id']][k] for k in ['initial_agreement','time_metadata_conflict','second_round_anomaly']})
    c.jsonl(c.OUT/'cohort.jsonl',rows)
    patients=sorted({r['sid'] for r in rows},key=lambda s:c.digest('092-outer-v1:'+s));folds=[]
    for k in range(5):
        test=patients[k::5];other=sorted(set(patients)-set(test),key=lambda s:c.digest('092-inner-v1:'+str(k)+':'+s));valid=other[:16];train=other[16:]
        assert len(train)==64 and len(valid)==16 and len(test)==20
        assert not set(train)&set(valid) and not set(train+valid)&set(test)
        folds.append(dict(fold=k,train=train,validation=valid,test=test))
    c.put(c.OUT/'folds.json',folds)
    from collections import Counter
    c.put(c.OUT/'fold_counts.json',[dict(fold=f['fold'],**{part:dict(N=len(rr),patients=len(f[part]),GT=dict(Counter(r['GT'] for r in rr))) for part in ['train','validation','test'] for rr in [[r for r in rows if r['sid'] in f[part]]]}) for f in folds])
if __name__=='__main__':main()
