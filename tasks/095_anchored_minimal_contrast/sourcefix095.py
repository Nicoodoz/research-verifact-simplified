"""Whitespace-only source-value binding repair; no semantic/prompt revision."""
import re
import method095 as original

def norm(s):return re.sub(r'\s+',' ',s).strip().lower()

def validate(v,row):
    result=original.validate(v,row)
    if result.get('error')!='value_not_in_quote':return result
    # All prior checks already passed. Reconstruct exact original anchors;
    # only whitespace differences in the literal value check are relaxed.
    refs=original.entries(row['reference']);anchors=[]
    for a in v['anchors']:
        ref=refs[a['reference_id']];start,end,quote=original.align(a['quote'],ref['text'])
        anchors.append(dict(reference_id=a['reference_id'],source_header=ref['header'],quote=quote,reference_start=ref['offset']+start,reference_end=ref['offset']+end))
    if not any(norm(v['source_value']) in norm(a['quote']) for a in anchors):return result
    claim=row['text'];old,new=v['old_span'],v['new_span'];start=claim.index(old)
    return dict(valid=True,attribute=v['attribute'],old_span=old,new_span=new,source_value=v['source_value'],edit_start=start,edit_end=start+len(old),alternative=claim[:start]+new+claim[start+len(old):],anchors=anchors)

def parse_builder(tr,row):
    try:return validate(original.object_from(tr),row)
    except (KeyError,TypeError,ValueError):return dict(valid=False,error='invalid_constructor_JSON')
