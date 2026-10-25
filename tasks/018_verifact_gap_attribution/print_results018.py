import common018 as c
if __name__=='__main__':
    metrics=c.read(c.OUT/'analysis_001/metrics.json');pairs=c.read(c.OUT/'analysis_001/paired.json')
    for q in ('010','016'):
        for a in ('llm','human'):
            print(q,a,'DELTA',c.canonical(pairs[q][a]['O_minus_C']['metrics']))
            for s,m in metrics[q][a].items():
                print(s,'MATRIX',m['confusion_matrix'],'RECALL',{k:round(v['recall'],4) for k,v in m['per_class'].items()})
    print('PATIENT BUCKETS',c.canonical([r for r in c.csvrows(c.OUT/'analysis_001/strata.csv') if r['dimension']=='subject_id' and r['cohort']!='pooled']))
    print('Q SENS',c.canonical(c.csvrows(c.OUT/'analysis_001/Qwen_sensitivity.csv')))
