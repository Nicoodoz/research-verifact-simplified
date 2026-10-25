"""Deterministic output-only examples, not new medical annotation."""
from common087 import *

def main():
    rows={x['id']:x for x in lines(OUT/'predictions.jsonl')}
    cases=lines(OUT/'attribution_cases.jsonl');selected={}
    for comparison in ('F4-X4','F4-CL4','F4-B'):
        for event in ('raw_rescue','raw_harm','rescue','harm'):
            pool=sorted((x for x in cases if x['comparison']==comparison and x[event]),key=lambda x:h('087/review/v1:'+x['id']))
            for x in pool[:1]:selected.setdefault(x['id'],[]).append(comparison+'/'+event)
    result=[]
    for pid,reasons in sorted(selected.items()):
        x=rows[pid];arms={}
        for a in ARMS:
            info=x['arms'][a];native=json.loads(read(ROOT/info['receipt_source'])['transport']['body_text'])
            content=native['choices'][0]['message'].get('content')
            try:obj=json.loads(content)
            except (ValueError,TypeError):obj={}
            arms[a]=dict(valid=info['valid'],raw=info['raw_verdict'],scores=info['scores'],final=x['labels'][a]['PriorG'],
                         reason=obj.get('reason'),receipt_source=info['receipt_source'])
        result.append(dict(id=pid,sid=x['sid'],GT=x['GT'],claim=x['claim'],selected_by=reasons,arms=arms,
                           interpretation_scope='Output wording only; clinician GT unchanged; no internal mechanism claim'))
    putl(OUT/'case_review_materials.jsonl',result)
    print(canonical(dict(n=len(result),cases=result)))

if __name__=='__main__':main()
