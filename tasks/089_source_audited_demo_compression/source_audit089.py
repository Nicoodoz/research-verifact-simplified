"""Describe actual interface/source failures without repairing frozen candidates."""
from collections import Counter
from common089 import *
from construct089 import all_ids,citation,render_reference
def main():
    fixed=read(OUT/'construction_summary.json');srcs=read(OUT/'source_units.json');coverage=read(OUT/'coverage_summary.json')['remaining'];rows=[]
    for scope,records in (('fixed',fixed),('coverage',coverage)):
        for r in records:
            if scope=='coverage' and r['status']!='constructed':continue
            src=srcs[r['id']] if scope=='fixed' else r['source_units']
            for arm in ('P4','Q4'):
                v=r[arm];obj=v.get('constructor_output');rank=obj.get('priority_ids') if isinstance(obj,dict) else None
                structural=[]
                if obj is not None:
                    if not isinstance(rank,list):structural.append('ranking_not_list')
                    elif any(not isinstance(i,str) for i in rank):structural.append('ranking_contains_objects_not_string_IDs')
                    # Diagnostic only: display potentially recoverable IDs, never mutate selection.
                    known=[i if isinstance(i,str) else i.get('id',i.get('unit_id')) if isinstance(i,dict) else None for i in (rank or [])]
                    missing=[i for i in all_ids(src) if i not in known]
                    if missing:structural.append('ranking_missing_'+','.join(missing))
                issues=[]
                for issue in (v.get('review_output') or {}).get('issues',[]):
                    issues.append(dict(issue=issue,quote_exact=citation(issue,src),unit_actually_deleted=issue.get('unit_id') not in v['initial_selected_ids'],
                        quote_present_after_whitespace_normalization=any(u['id']==issue.get('unit_id') and ' '.join(issue.get('quote','').split()) in ' '.join(u['text'].split()) for u in src['units'])))
                rows.append(dict(scope=scope,id=r['id'],arm=arm,status=v['status'],structural_issues=structural,original_chars=r['original_chars'],
                    final_chars=len(render_reference(src,v['selected_ids'])),compressed=len(v['selected_ids'])<len(src['units']),
                    source_units=len(src['units']),selected_units=len(v['selected_ids']),constructor_called='constructor_receipt' in v,
                    review_called='review_receipt' in v,repair_units=v.get('added_ids',[]),accepted_issues=v.get('accepted_issues',[]),review_issue_diagnostics=issues))
    put(OUT/'source_audit.json',dict(rows=rows,summaries={scope:dict(arms=len(z),constructed_calls=sum(r['constructor_called'] for r in z),
        review_calls=sum(r['review_called'] for r in z),compressed_arms=sum(r['compressed'] for r in z),status=dict(Counter(r['status'] for r in z)),
        arms_with_repair=sum(bool(r['repair_units']) for r in z)) for scope in ('fixed','coverage') for z in [[r for r in rows if r['scope']==scope]]},
        note='Post-freeze diagnostic only; no alternative parser/candidates or new downstream selection'))
    print(canonical(read(OUT/'source_audit.json')['summaries']))
if __name__=='__main__':main()
