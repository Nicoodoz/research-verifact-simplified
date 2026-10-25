"""Fixed source priority; preserve original fallback and reference bindings."""
import json
import common092 as c
SOURCES=['078_component_ablation/predictions.jsonl','078_component_ablation/f4_extension_001/predictions.jsonl','082_anchor_configuration_adaptation/evaluation_predictions.jsonl','084_f4_coverage_validation/new_predictions.jsonl','090_demo_constructor_repair_validation/predictions_public.jsonl']
def main():
    refs={r['proposition_id']:r for r in c.lines(c.PRIVATE/'cached_c48.jsonl')};cohort={r['id']:r for r in c.lines(c.OUT/'cohort.jsonl')};records={};sources={}
    eval082={j['body_sha256']:j['body'] for j in c.lines(c.ROOT/'outputs/082_anchor_configuration_adaptation/eval_jobs.jsonl')}
    for source in SOURCES:
        p=c.ROOT/'outputs'/source;sources[source]=c.sha(p)
        for r in c.lines(p):
            pid=r['id'];assert r['GT']==cohort[pid]['GT'];assert str(r['sid'])==cohort[pid]['sid']
            for dest,arm in [('B','TS' if source.startswith('078') else 'B'),('F4','F4')]:
                if (pid,dest) in records or arm not in r['arms']:continue
                aa=r['arms'][arm]
                if source.startswith('078'):
                    mm=r['methods'][arm+'_PriorG'];label=mm['label'];fallback=mm['fallback'];body=c.read(c.ROOT/aa['request_source'])['job']['body'];payload=json.loads(body['messages'][-1]['content']);ref=payload['reference'];claim=payload['proposition'];assert claim==refs[pid]['text'];rh=c.digest(ref)
                else:
                    label=r.get('methods',r.get('labels'))[dest]['PriorG'];fallback=not aa['valid'];rh=r.get('reference_sha256')
                    if rh is None:
                        # 082 target materials are frozen 032; compare the request when no explicit hash exists.
                        if 'request_source' in aa:
                            body=c.read(c.ROOT/aa['request_source'])['job']['body'];payload=json.loads(body['messages'][-1]['content']);rh=c.digest(payload['reference'])
                        else:
                            payload=json.loads(eval082[aa['body_sha256']]['messages'][-1]['content']);assert payload['proposition']==refs[pid]['text'];rh=c.digest(payload['reference'])
                assert rh==c.digest(refs[pid]['reference']),('C48 mismatch',pid,source)
                records[pid,dest]=dict(id=pid,arm=dest,label=label,raw=aa.get('raw',aa.get('raw_verdict')),scores=aa.get('scores'),valid=aa['valid'],fallback=fallback,source=source,body_sha256=aa['body_sha256'],reference_sha256=rh,panel=r.get('panel'),source_reference_hash_explicit=('reference_sha256' in r or source.startswith('078')))
    c.jsonl(c.OUT/'cached_baselines.jsonl',[records[k] for k in sorted(records)]);c.put(c.OUT/'baseline_sources.json',sources);print('cached baseline arm positions',len(records))
if __name__=='__main__':main()
