"""Synthetic metric/selection regression, without reading clinical predictions or GT."""
import common099 as c
import analyze099 as a

def main():
    rows=[dict(id=str(i),sid=str(i//3),GT=c.LABELS[i%3],author='fixture',predictions=dict(Original=c.LABELS[i%3],good=c.LABELS[i%3],bad=c.LABELS[(i+1)%3])) for i in range(12)]
    p=a.pair(rows,'good','bad')
    assert p['rescue']==0 and p['harm']==12 and p['net']==-12 and p['false_S_added']==4
    assert a.metric(rows,'good')['mcc']==1 and a.metric(rows,'bad')['percent_agreement']==0
    r=[dict(x,predictions=dict(Original=x['GT'],**{m:None for m in c.MODELS})) for x in rows]
    empty=a.panel(r,list(c.MODELS))
    assert empty['common_N']==0 and empty['tables']=={} and all(x['invalid']==12 for x in empty['coverage'].values())
    # Equal quality falls through to the predeclared matched-cost choice.
    t=dict(mcc=.5,percent_agreement=.8,false_S=2,per_class={lab:dict(recall=.5) for lab in c.LABELS})
    main=dict(tables={m:t.copy() for m in ['Original']+list(c.MODELS)},coverage={m:dict(valid=80,frozen_N=80) for m in c.MODELS})
    diag=dict(tables={m:t.copy() for m in c.MODELS})
    costs={m:dict(mean_no_cache_cny=x) for m,x in zip(c.MODELS,[.003,.03,.005,.002])}
    selected=a.select(main,diag,costs)
    assert selected['primary']=='qwen3.5-35b-a3b' and 'qwen3.8-flash' not in selected['eligible']
    c.put(c.OUT/'analysis_fixture_checks.json',dict(utc=c.utc(),status='PASS',synthetic_only=True,clinical_quality_not_read=True,
          checks=['official metrics and false-S transitions','zero-valid explicit handling','predeclared cost tie-break and deployment gate']))
    print('099 synthetic metric/selection checks PASS; no clinical quality read')

if __name__=='__main__':main()
