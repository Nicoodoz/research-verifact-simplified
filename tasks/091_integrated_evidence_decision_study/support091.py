"""Small source-bound audit of manuscript anchor tables and saved repeats."""
from common091 import *
def main():
    paths=[ROOT/'outputs/078_component_ablation/predictions.jsonl',ROOT/'outputs/078_component_ablation/f4_extension_001/predictions.jsonl',ROOT/'outputs/082_anchor_configuration_adaptation/evaluation_predictions.jsonl',ROOT/'outputs/082_anchor_configuration_adaptation/repeat_predictions.jsonl',ROOT/'outputs/086_global_demonstration_selection/E_predictions.jsonl',ROOT/'outputs/086_global_demonstration_selection/V_old_new_F4_bridge.json',ROOT/'outputs/090_demo_constructor_repair_validation/predictions_public.jsonl']
    r=lines(paths[0]);codes=('Original','NS_raw','NS_U2','GateA','NS_StdM','NS_StdV','TS_raw','TS_prior','TS_PriorG')
    table={k:metrics([x['GT'] for x in r],[x['methods'][k]['label'] for x in r]) for k in codes}
    assert [table[k]['correct'] for k in codes]==[310,284,310,307,320,319,289,321,321]
    assert all(x['methods']['TS_prior']['label']==x['methods']['TS_PriorG']['label'] for x in r)
    ev={x['id']:x for x in lines(paths[2])};rep=lines(paths[3]);repeat={}
    for a in ('B','F4'):
        for x in rep:assert x['arms'][a]['body_sha256']==ev[x['id']]['arms'][a]['body_sha256']
        repeat[a]={m:dict(flips=sum(x['methods'][a][m]!=x['original_methods'][a][m] for x in rep),first_correct=sum(x['original_methods'][a][m]==x['GT'] for x in rep),repeat_correct=sum(x['methods'][a][m]==x['GT'] for x in rep)) for m in ('raw','U0','U2','PriorG')}
    e=lines(paths[4]);bridge={};extra=[]
    for x in e:
        p=(ROOT/x['arms']['F4_old']['source']).parent/'request.json';extra.append(p);j=read(p)['job']
        assert h(canonical(j['body']))==j['body_sha256']==x['arms']['F4_new']['body_sha256']
    for m in ('raw','PriorG'):
        bridge[m]=dict(flips=sum(x['labels']['F4_old'][m]!=x['labels']['F4_new'][m] for x in e),first_correct=sum(x['labels']['F4_old'][m]==x['GT'] for x in e),repeat_correct=sum(x['labels']['F4_new'][m]==x['GT'] for x in e))
    # Limited, declared caches only. Same ID is insufficient: exact request SHA required.
    history={}
    for p in paths[:5]:
        for x in lines(p):
            for arm,v in x.get('arms',{}).items():
                b=v.get('body_sha256')
                if b:history.setdefault((x['id'],b),[]).append(dict(path=p.relative_to(ROOT).as_posix(),arm=arm,receipt=v.get('receipt_source')))
    rows=lines(paths[-1]);matches=[]
    for x in rows:
        for a,v in x['arms'].items():
            match=history.get((x['id'],v['body_sha256']),[])
            if match:matches.append(dict(id=x['id'],panel=x['panel'],arm=a,sources=match))
    out=dict(source_sha256=bind(paths+extra),table078=table,repeat082=dict(n=len(rep),patients=len({x['sid'] for x in rep}),GT=dict(Counter(x['GT'] for x in rep)),arms=repeat),bridge086_E=dict(n=len(e),arms=bridge),bridge086_V=read(paths[5]),repeat090_inventory=dict(matched_body_records=len(matches),counts=dict(Counter(x['arm'] for x in matches)),matches=matches,scope='078 main/extension,082 eval/repeat,086 E only; cached duplicate receipt references do not count as independent repeats. P90 has no historical matched body in these declared caches.'))
    put(OUT/'historical_anchor_checks.json',out)
    print(canonical(dict(repeat082=out['repeat082'],bridge086_E=out['bridge086_E'],matches090=out['repeat090_inventory']['counts'])))
if __name__=='__main__':main()
