"""090 exact-body bridges: earliest saved receipt, never outcome-selected."""
from common091 import *
def main():
    m=read(OUT/'historical_anchor_checks.json')['repeat090_inventory']['matches'];new={x['id']:x for x in lines(ROOT/'outputs/090_demo_constructor_repair_validation/predictions_public.jsonl')};cache={};rows=[]
    for item in m:
        choices=[]
        for s in item['sources']:
            if s['path'] not in cache:cache[s['path']]={x['id']:x for x in lines(ROOT/s['path'])}
            x=cache[s['path']][item['id']];a=s['arm'];v=x['arms'][a];p=(ROOT/s['receipt']).parent/'request.json';req=read(p)
            body=req['job']['body'];assert h(canonical(body))==new[item['id']]['arms'][item['arm']]['body_sha256']
            if 'methods' in x:
                if a in x['methods']:lab=x['methods'][a]
                else:lab={k:x['methods'][a+'_'+k]['label'] for k in ('raw','PriorG')}
            else:lab=x['labels'][a]
            stamp=req.get('created_utc') or read(ROOT/s['receipt'])['transport']['started_utc']
            stamp=datetime.datetime.fromisoformat(stamp).astimezone(datetime.timezone.utc).isoformat()
            choices.append((stamp,s['receipt'],lab,v))
        earliest=min(choices,key=lambda x:x[:2]);x=new[item['id']];a=item['arm']
        rows.append(dict(id=x['id'],sid=x['sid'],panel=x['panel'],arm=a,GT=x['GT'],old_created_utc=earliest[0],old_receipt=earliest[1],old_valid=earliest[3]['valid'],new_valid=x['arms'][a]['valid'],old={k:earliest[2][k] for k in ('raw','PriorG')},new={k:x['labels'][a][k] for k in ('raw','PriorG')}))
    summary={}
    for a in ('B','F4'):
        allr=[x for x in rows if x['arm']==a];valid=[x for x in allr if x['old_valid'] and x['new_valid']]
        summary[a]=dict(full_n=len(allr),common_core_n=len(valid),patients=len({x['sid'] for x in valid}),panel_counts=dict(Counter(x['panel'] for x in valid)),layers={k:dict(old_correct=sum(x['old'][k]==x['GT'] for x in valid),new_correct=sum(x['new'][k]==x['GT'] for x in valid),flips=sum(x['old'][k]!=x['new'][k] for x in valid),rescues=sum(x['old'][k]!=x['GT'] and x['new'][k]==x['GT'] for x in valid),harms=sum(x['old'][k]==x['GT'] and x['new'][k]!=x['GT'] for x in valid)) for k in ('raw','PriorG')})
    put(OUT/'B_repeat090.json',dict(summary=summary,rows=rows,selection='earliest created_utc then receipt path among predeclared exact-body sources; duplicated references count once',P90_repeat_n=0,limitation='Retrospective historical bridge, not randomized repeat and not a P90 repeat. Cannot attribute all differences to stochastic sampling rather than service time.'))
    print(canonical(summary))
if __name__=='__main__':main()
