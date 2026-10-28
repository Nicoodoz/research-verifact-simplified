"""One frozen parser for all three arms; no GT, repair model or fallback label."""
import json
import re
from common105 import LABELS

def parse(content,finish_reason='stop'):
    def pairs(items):
        out={}
        for key,value in items:
            if key in out:raise ValueError('Duplicate key')
            out[key]=value
        return out
    try:
        if finish_reason!='stop' or not isinstance(content,str):raise ValueError('Incomplete generation')
        fenced=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',content,re.S|re.I)
        text=fenced[1] if fenced else content.strip()
        if text in LABELS:return dict(valid=True,verdict=text,exact_label_normalized=True,strict_json=False)
        value=json.loads(text,object_pairs_hook=pairs)
        if not isinstance(value,dict) or value.get('verdict') not in LABELS:raise ValueError('Missing/invalid final verdict')
        return dict(valid=True,verdict=value['verdict'],exact_label_normalized=False,strict_json=True)
    except (ValueError,TypeError):return dict(valid=False,verdict=None,exact_label_normalized=False,strict_json=False)
