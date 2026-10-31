"""Rank all intact original reference fragments using the unchanged008 BM25."""
from collections import Counter
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
import ast,copy,math,re
import numpy as np

LEXICAL_SOURCE=Path(__file__).resolve().parents[1]/'008_retrieval_planning/planning_core.py'
HEADER=re.compile(r'(?m)^(\d+)\. (Date: [^\n]*? \| Text: )')


@lru_cache(maxsize=1)
def _legacy_functions():
    """Load exact008 lexical code without importing its unrelated data pipeline."""
    tree=ast.parse(LEXICAL_SOURCE.read_text(encoding='utf-8-sig'))
    stop=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STOP' for t in n.targets))
    tokenize=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='tokenize')
    index=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='HybridIndex')
    bm25=copy.deepcopy(next(n for n in index.body if isinstance(n,ast.FunctionDef) and n.name=='bm25'))
    bm25.name='legacy_bm25'
    module=ast.fix_missing_locations(ast.Module(body=[stop,tokenize,bm25],type_ignores=[]))
    namespace={'re':re,'math':math,'np':np}
    exec(compile(module,str(LEXICAL_SOURCE),'exec'),namespace)
    return namespace['tokenize'],namespace['legacy_bm25']


def split_reference(reference: str):
    """Return unchanged prefix and numbered raw spans; never infer note identity."""
    if not isinstance(reference,str):raise TypeError('reference must be str')
    matches=list(HEADER.finditer(reference))
    if not matches:raise ValueError('No original numbered Date/Text fragment headers')
    units=[]
    for i,match in enumerate(matches):
        end=matches[i+1].start() if i+1<len(matches) else len(reference)
        units.append(dict(number=match.group(1),start=match.start(),end=end,
            header=reference[match.start():match.end()],metadata=match.group(2),
            text=reference[match.end():end],raw=reference[match.start():end]))
    if len({u['number'] for u in units})!=len(units):raise ValueError('Ambiguous duplicate original fragment numbers')
    prefix=reference[:matches[0].start()]
    if prefix+''.join(u['raw'] for u in units)!=reference:raise AssertionError('Source partition changed text')
    return prefix,units


def _scores(claim,units):
    tokenize,bm25=_legacy_functions()
    counts=[Counter(tokenize(u['metadata']+u['text'])) for u in units]
    lengths=np.array([sum(c.values()) for c in counts]);postings={}
    for i,count in enumerate(counts):
        for token,n in count.items():postings.setdefault(token,[]).append((i,n))
    # Integer passage IDs keep008's own tie ordering consistent with original order.
    index=SimpleNamespace(passages=[{'passage_id':i} for i in range(len(units))],
        counts=counts,lengths=lengths,average=float(lengths.mean()),postings=postings)
    positive=dict(bm25(index,claim))
    return [positive.get(i,0.) for i in range(len(units))]


def reorder_reference(reference: str, claim: str) -> tuple[str,dict]:
    """Return reordered complete reference plus losslessness/order manifest."""
    if not isinstance(claim,str):raise TypeError('claim must be str')
    prefix,units=split_reference(reference);scores=_scores(claim,units)
    order=sorted(range(len(units)),key=lambda i:(-scores[i],i))
    parts=[prefix];cursor=len(prefix);spans=[];separators=[]
    for position,i in enumerate(order):
        unit=units[i];start=cursor;parts.append(unit['raw']);cursor+=len(unit['raw'])
        spans.append(dict(number=unit['number'],original_start=unit['start'],original_end=unit['end'],
            rendered_start=start,rendered_end=cursor,score=scores[i]))
        if position+1<len(order) and not unit['raw'].endswith('\n'):
            separators.append(dict(after_fragment=unit['number'],rendered_offset=cursor,text='\n'))
            parts.append('\n');cursor+=1
    rendered=''.join(parts)
    original=Counter(u['raw'] for u in units)
    retained=Counter(rendered[s['rendered_start']:s['rendered_end']] for s in spans)
    if original!=retained:raise AssertionError('Fragment multiset changed')
    if len(HEADER.findall(rendered))!=len(units):raise AssertionError('Rendered fragment boundary changed')
    manifest=dict(operation='relevance_order',original_fragment_order=[u['number'] for u in units],
        new_fragment_order=[units[i]['number'] for i in order],fragment_N=len(units),
        added_separator_chars=len(separators),added_separators=separators,
        original_characters=len(reference),rendered_characters=len(rendered),
        original_prefix_preserved=rendered.startswith(prefix),fragment_multiset_preserved=True,
        original_numbers_preserved=True,headers_and_text_unchanged=True,
        no_deletion_truncation_or_rewrite=True,zero_score_fragments_retained=True,
        stable_original_order_for_ties=True,zero_score_fragment_N=sum(s==0 for s in scores),
        bm25_source='tasks/008_retrieval_planning/planning_core.py:tokenize,HybridIndex.bm25',
        score_input='original metadata+Text; no GT, reason or evidence_span',
        fragments=spans)
    return rendered,manifest
