"""GT-blind, single whole-passage replacements; no prompt/packing modification."""
from collections import Counter
import math
import common017 as c

def render(ids,item,passages):
    return c.core.select_evidence(ids,item['scores'],passages,item['admission'])

def token_set(text):
    # No absolute dates, patient IDs, author/source labels or raw bag-of-words features.
    return {t for t in c.core.tokenize(text) if t.isalpha()}

def features(item,pid,kept,passages):
    p=passages[pid];tokens=token_set(p['text']);claim=token_set(item['text'])
    ranks={k:{pid:i for i,(pid,_) in enumerate(item['rankings'][k],1)} for k in ('dense','bm25')}
    order=sorted(item['wide'],key=lambda k:(-item['scores'][k],k));brank=order.index(pid)+1
    redundancy=max((len(tokens&token_set(passages[k]['text']))/max(1,len(tokens|token_set(passages[k]['text']))) for k in kept),default=0.)
    return [item['scores'][pid],1/brank,1/ranks['dense'][pid] if pid in ranks['dense'] else 0.,
        1/ranks['bm25'][pid] if pid in ranks['bm25'] else 0.,math.log1p(len(p['text']))/math.log(8001),
        len(tokens&claim)/max(1,len(claim)),redundancy,sum(passages[k]['note_id']==p['note_id'] for k in kept)/2]

def proposal(item,passages,arm):
    selected=item['baseline']['selected_ids'];chosen=set(selected)
    incoming=[k for k in (item['wide'] if arm=='wide_swap' else item['C48']) if k not in chosen and (arm!='wide_swap' or k not in item['C48'])]
    incoming.sort(key=lambda k:(-item['scores'][k],k))
    outgoing=sorted(selected,key=lambda k:(item['scores'][k],k))
    for pin in incoming:
        for pout in outgoing:
            same=passages[pin]['note_id']==passages[pout]['note_id']
            if arm=='c48_local' and not same or arm=='c48_crossnote' and same:continue
            kept=[k for k in selected if k!=pout];candidate=kept+[pin]
            if max(Counter(passages[k]['note_id'] for k in candidate).values())>2:continue
            packed=render(candidate,item,passages)
            if set(packed['selected_ids'])!=set(candidate) or len(candidate)!=len(selected):continue
            ratio=packed['body_characters']/max(1,item['baseline']['body_characters'])
            if not .90<=ratio<=1.10 or packed['reference']==item['baseline']['reference']:continue
            return dict(eligible=True,added=pin,removed=pout,kept=kept,reference=packed['reference'],selected_ids=packed['selected_ids'],
                body_characters=packed['body_characters'],length_ratio=ratio,features_in=features(item,pin,kept,passages),features_out=features(item,pout,kept,passages))
    return dict(eligible=False,added=None,removed=None,reference=item['baseline']['reference'],selected_ids=selected,
        body_characters=item['baseline']['body_characters'],length_ratio=1.,features_in=None,features_out=None)

def interventions(item,passages):
    reconstructed=render(item['C48'],item,passages)
    c.require(reconstructed['reference']==item['baseline']['reference'],'Original C48 reconstruction differs')
    result={'baseline':dict(item['baseline'],eligible=True)}
    result.update({arm:proposal(item,passages,arm) for arm in c.SWAPS})
    wide=render(item['wide'],item,passages)
    result['wide_relevance']=dict(wide,eligible=wide['reference']!=item['baseline']['reference'])
    return result
