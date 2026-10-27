"""Categorize frozen failures without repairing responses or re-evaluating alternate labels."""
from collections import Counter
import json
import common101 as c,runtime101 as rt,prompts101 as p
def main():
 done=rt.completed();materials={r['id']:r for r in c.lines(c.PRIVATE/'materials.jsonl')};records=[]
 for r in c.lines(c.OUT/'parsed_reviews.jsonl'):
  if r['valid'] or r['repeat']:continue
  response=json.loads(c.read(done[r['request_id']]/'receipt.json')['transport']['body_text']);choice=response['choices'][0];content=choice['message'].get('content') or ''
  category='outer_markdown_fence' if content.strip().startswith('```') else 'unlocatable_quote' if any(e=='unlocatable_quote' for e in r['errors']) else 'empty_content' if not content.strip() else 'schema_or_finish'
  records.append(dict(id=r['id'],arm=r['arm'],category=category,finish_reason=choice.get('finish_reason'),errors=r['errors']))
 a=c.read(c.OUT/'analysis.json');changes={arm:Counter((x['GT'],x['kind'],x['base'],x['candidate']) for x in a['paired']['natural'][arm+'__vs__verifact_ref']['changes']) for arm in c.REVIEW_ARMS}
 c.put(c.OUT/'format_diagnostics.json',dict(first_review_fallbacks=len(records),counts=dict(Counter(r['category'] for r in records)),finish_reasons=dict(Counter(r['finish_reason'] for r in records)),records=records,no_parser_or_prediction_changes=True,natural_changes={arm:[dict(GT=g,kind=k,base=b,candidate=p,count=n) for (g,k,b,p),n in sorted(cc.items())] for arm,cc in changes.items()}))
 print(c.canonical(dict(categories=dict(Counter(r['category'] for r in records)),finish=Counter(r['finish_reason'] for r in records),wrong_to_wrong={arm:sum(n for (g,k,b,p),n in cc.items() if k=='wrong_to_wrong') for arm,cc in changes.items()})))
if __name__=='__main__':main()
