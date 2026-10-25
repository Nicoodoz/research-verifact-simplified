"""Whitespace-only source alignment; restore actual source bytes, never repair semantics."""
import re
import common094 as c
import method094 as m
def parse(tr,reference):
    try:
        o=m.obj(tr);assert o['status'] in ['answered','ambiguous','insufficient'] and isinstance(o['candidates'],list) and len(o['candidates'])<=2
        assert (o['status']=='insufficient')==(len(o['candidates'])==0)
        refs=m.entries(reference);clean=[];citations=[];normalized=0
        for r in o['candidates']:
            for k,n in [('answer',200),('time',100),('state',80)]:assert isinstance(r[k],str) and 0<len(r[k])<=n
            assert 1<=len(r['evidence'])<=2
            ev=[]
            for e in r['evidence']:
                rid=e['reference_id'];quote=e['quote'];assert type(rid)is int and isinstance(quote,str) and 0<len(quote)<=200
                source=refs.get(rid,'');match=re.search(r'\s+'.join(re.escape(x) for x in quote.split()),source)
                assert match is not None
                actual=match.group();assert len(actual)<=500
                normalized+=actual!=quote
                ev.append(dict(reference_id=rid,quote=actual));citations.append(dict(reference_id=rid,quote_sha256=c.h(actual),entry_start=match.start(),entry_end=match.end(),whitespace_normalized=actual!=quote))
            clean.append({**{k:r[k] for k in ['answer','time','state']},'evidence':ev})
        record=dict(status=o['status'],candidates=clean);assert len(c.canonical(record).encode())<=4000
        return dict(valid=True,record=record,citations=citations,whitespace_normalizations=normalized)
    except (ValueError,KeyError,TypeError,AssertionError):return dict(valid=False,record=dict(status='unavailable_invalid_auxiliary_output',candidates=[]),citations=[],whitespace_normalizations=0)
