"""Attach a rationale to an immutable verdict, exposing failures instead of inventing one."""
import json,re
LABELS=('Supported','Not Supported','Not Addressed')

def package_reason(fixed_verdict,generated_text,reference,*,finish_reason='stop',reviewed_stance=None,label_only=False):
    if fixed_verdict not in LABELS:raise ValueError('Unknown fixed model verdict')
    if not isinstance(reference,str):raise TypeError('Full actual reference required')
    result=dict(verdict=fixed_verdict,reason=None,reason_status='generation_failed',direction_reviewed=reviewed_stance is not None,flags=[])
    if finish_reason!='stop':result['flags'].append('generation_'+finish_reason);return result
    try:value=json.loads(generated_text)
    except (ValueError,TypeError):result['flags'].append('invalid_JSON');return result
    if not isinstance(value,dict) or value.get('status') not in ('explained','unable'):
        result['flags'].append('invalid_schema');return result
    if value['status']=='unable':result['reason_status']='unable';return result
    reason=value.get('reason')
    if not isinstance(reason,str) or not reason.strip():result['flags'].append('empty_reason');return result
    dates=set(re.findall(r'\b\d{4}-\d{2}-\d{2}\b',reason))
    if any(date not in reference for date in dates):result['flags'].append('ISO_date_not_in_reference')
    if reviewed_stance is not None and reviewed_stance!=fixed_verdict:result['flags'].append('direction_conflict_or_ambiguous')
    if label_only:result['flags'].append('label_only_explanation')
    if result['flags']:result['reason_status']='needs_review';return result
    result['reason']=reason.strip();result['reason_status']='ready' if reviewed_stance is not None else 'direction_unreviewed'
    return result
