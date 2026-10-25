"""Additive check of native-only rows and inherited descriptive metadata."""
from collections import Counter
from common090 import *
from verify090 import independent_metric

def main():
    rows=lines(OUT/'predictions.jsonl');a=read(OUT/'analysis.json');checks=[];corrections=[]
    for panel in ('natural','pressure'):
        z=[r for r in rows if r['panel']==panel and all(r['arms'][arm]['raw_valid'] for arm in ARMS)]
        assert len(z)==a['panels'][panel]['raw_common_n']
        for arm in ARMS:
            assert all(r['labels'][arm]['raw']==r['arms'][arm]['raw_verdict'] and not r['arms'][arm]['raw_fallback_used'] for r in z)
            m=independent_metric(z,arm,'raw');old=a['panels'][panel]['native_raw_metrics'][arm]
            for k,v in m.items():assert abs(v-old[k])<1e-12 if isinstance(v,float) else v==old[k]
            checks.append(dict(panel=panel,arm=arm,n=len(z),actual_raw_fallbacks=0,**m))
            if old['raw_includes_fallback']:
                corrections.append(dict(json_path=f'panels.{panel}.native_raw_metrics.{arm}.raw_includes_fallback',stored=True,correct=False))
    put(PUB/'raw_validity_check.json',dict(status='PASS',independent_audit=False,rows=checks))
    put(PUB/'analysis_metadata_correction.json',dict(
        reason='Shared legacy metric helper flags any core-invalid record as raw fallback, including records with a valid native verdict. The native-only labels and numeric metrics are correct; these descriptive flags are false. Frozen analysis/code retained unchanged.',
        corrections=corrections,analysis_sha256=sha(OUT/'analysis.json'),numeric_metrics_changed=False))
    ats=lines(OUT/'attribution_cases.jsonl')
    for panel in ('natural','pressure'):
        d=a['panels'][panel]
        print(canonical(dict(panel=panel,core_n=d['common_core_n'],raw_n=d['raw_common_n'],
            correct={m:{arm:v['correct'] for arm,v in metrics.items()} for m,metrics in d['full_metrics'].items()},
            attribution={comp:{kind:dict(rescue=sum(x['rescue'] for x in ats if x['panel']==panel and x['comparison']==comp and x['kind']==kind),harm=sum(x['harm'] for x in ats if x['panel']==panel and x['comparison']==comp and x['kind']==kind)) for kind in ('invalid_or_fallback_related','raw_correctness_change','valid_score_boundary_change')} for comp in ('P90-F4','P90-Q90')},
            invalids={arm:dict(Counter((r['arms'][arm]['status']+' / '+str(r['arms'][arm]['finish_reason'])) for r in rows if r['panel']==panel and not r['arms'][arm]['valid'])) for arm in ARMS})))
    print(canonical(dict(native_metrics_verified=True,metadata_corrections=corrections)))

if __name__=='__main__':main()
