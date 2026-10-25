"""Reuse existing exact-input B repetitions; no calls, no best-answer selection."""
from collections import defaultdict,Counter
import json
import common095 as c
import state095 as s
from cache095 import parse_arm,signature
from metrics095 import score,paired

def main():
    meta={r['id']:r for r in c.lines(c.ROOT/'outputs/092_task_adapted_verifier/cohort.jsonl')};bags=defaultdict(list)
    for r in c.lines(c.OUT/'cache_candidates.jsonl'):bags[r['id']].append(r)
    sig=c.read(c.OUT/'cache_inventory.json')['template_signature'];refs={r['id']:r for r in c.lines(c.OUT/'reference_inventory.jsonl')}
    for rid,x in s.successful_jobs().items():
        j=x['job']
        if j['arm']!='B':continue
        assert signature(j['body'])==sig
        payload=json.loads(j['body']['messages'][1]['content']);ref=refs[j['id']]
        assert set(payload)=={'proposition','reference'}
        assert c.h(payload['proposition'])==ref['claim_sha256'] and c.h(payload['reference'])==ref['reference_sha256']
        p,labels=parse_arm(s.receipt(x),None)
        bags[j['id']].append(dict(id=j['id'],time=x['utc'],request_path=x['folder']+'/request.json',body_sha256=j['body_sha256'],parsed=p,labels=labels))
    out=[]
    for pid,bag in bags.items():
        if len(bag)<2:continue
        bag=sorted(bag,key=lambda r:(r['time'],r['request_path']));a,b=bag[0],bag[-1]
        out.append(dict(id=pid,sid=meta[pid]['sid'],GT=meta[pid]['GT'],Original=meta[pid]['original'],N_receipts=len(bag),first_time=a['time'],last_time=b['time'],first_source=a['request_path'],last_source=b['request_path'],first=a['labels'],last=b['labels'],first_scores=a['parsed']['scores'],last_scores=b['parsed']['scores'],same_body_bytes=a['body_sha256']==b['body_sha256'],common_core=a['parsed']['valid'] and b['parsed']['valid'],common_raw=a['parsed']['raw_valid'] and b['parsed']['raw_valid'],raw_changed=a['labels']['raw']!=b['labels']['raw'],final_changed=a['labels']['PriorG']!=b['labels']['PriorG']))
    analysis={}
    for method in ['raw','PriorG']:
        chosen=[r for r in out if r['common_raw' if method=='raw' else 'common_core']];rows=[dict(id=r['id'],sid=r['sid'],GT=r['GT'],predictions=dict(Original=r['Original'],first=r['first'][method],last=r['last'][method]),probabilities={}) for r in chosen]
        analysis[method]=dict(N=len(rows),metrics=score(rows,['Original','first','last']),paired=paired(rows,'first','last'),label_changes=sum(r['first'][method]!=r['last'][method] for r in chosen))
    bridge=[]
    sp=c.OUT/'screen_predictions.jsonl';selected={r['id']:r for r in c.lines(c.OUT/'cache_selected.jsonl')}
    if sp.exists():
        for r in c.lines(sp):
            if r['id'] not in selected:continue
            a=selected[r['id']];bridge.append(dict(id=r['id'],sid=r['sid'],GT=r['GT'],panel=r['panel'],old=a['labels'],fresh=r['labels']['B'],common_core=a['parsed']['valid'] and r['arms']['B']['valid'],common_raw=a['parsed']['raw_valid'] and r['arms']['B']['raw_valid'],old_source=a['request_path'],fresh_request_id=r['arms']['B']['request_id']))
    ba={}
    for panel in ['natural','mechanism']:
        ba[panel]={}
        for method in ['raw','PriorG']:
            rr=[r for r in bridge if r['panel']==panel and r['common_raw' if method=='raw' else 'common_core']];vv=[dict(id=r['id'],sid=r['sid'],GT=r['GT'],predictions={'old':r['old'][method],'fresh':r['fresh'][method]},probabilities={}) for r in rr]
            ba[panel][method]=dict(N=len(rr),metrics=score(vv,['old','fresh']),paired=paired(vv,'old','fresh'),label_changes=sum(r['old'][method]!=r['fresh'][method] for r in rr))
    c.putl(c.OUT/'existing_B_repeats.jsonl',out);c.putl(c.OUT/'screen_B_batch_bridge.jsonl',bridge);c.put(c.OUT/'repeat_analysis.json',dict(existing=analysis,bridge=ba,note='Earliest/latest existing compatible successful B only, invalid kept. Repeated subset is historical/development selected, not an unbiased estimate of service variance; no extra repeat calls, no winner replacement. Exact user text and normalized default request configuration, byte identity also recorded.'))
    print('existing repeated IDs',len(out),'D historical/fresh bridge',len(bridge))
if __name__=='__main__':main()
