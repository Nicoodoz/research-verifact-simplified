import json,re
LABELS=('Supported','Not Supported','Not Addressed')
def parse_content(content,finish=None):
 try:
  assert isinstance(content,str)
  match=re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*',content,re.S|re.I)
  if match:content=match[1]
  def pairs(items):
   d={}
   for k,v in items:
    if k in d:raise ValueError('duplicate key')
    d[k]=v
   return d
  obj=json.loads(content,object_pairs_hook=pairs);assert isinstance(obj,dict) and obj.get('verdict') in LABELS
  return dict(verdict=obj['verdict'],valid=True,reason_present=bool(str(obj.get('reason','')).strip()),finish_reason=finish,outer_fence_removed=bool(match),format_anomaly=finish not in [None,'stop'])
 except (ValueError,TypeError,AssertionError):return dict(verdict=None,valid=False,finish_reason=finish,format_anomaly=True)
def parse(tr):
 try:
  assert tr['http_status']==200
  choice=json.loads(tr['body_text'])['choices'][0]
  return parse_content(choice['message'].get('content'),choice.get('finish_reason'))
 except (ValueError,TypeError,KeyError,AssertionError,IndexError):return dict(verdict=None,valid=False,format_anomaly=True)
