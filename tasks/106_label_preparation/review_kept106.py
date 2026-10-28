"""Verify private manual source-review spans; publish only abstract metadata."""
import common106 as c

def main():
    dossiers={r['id']:r for r in c.rows(c.PRIVATE/'A_source_review_dossiers.jsonl')}
    decisions=c.read(c.PRIVATE/'semantic_A_kept_manual.json');public=[];private=[]
    for decision in decisions:
        d=dossiers[decision['id']];ref=d['full_reference'];record={k:v for k,v in decision.items() if not k.endswith('_quotes')}
        if c.digest(ref)!=d['reference_sha256']:raise ValueError('Reference changed')
        record.update(sid=d['sid'],GT=d['GT'],before=d['before'],after=d['after'],panel=d['panel'],groups=d['groups'],
            reference_sha256=d['reference_sha256'],claim_sha256=d['claim_sha256'],complete_reference_read=True,
            read_character_ranges=[[0,len(ref)]],read_scope='complete_actual_reference_not_full_EHR',
            review_type='Codex_source_review_not_new_doctor_GT',GT_unchanged=True,no_training_or_prompt_examples=True)
        for key in ('decisive','counterevidence'):
            spans=[]
            for quote in decision[key+'_quotes']:
                start=0;occurrences=[]
                while True:
                    start=ref.find(quote,start)
                    if start<0:break
                    occurrences.append(dict(start=start,end=start+len(quote)));start+=1
                if not occurrences:raise ValueError('Quotation does not match '+decision['id']+' '+key)
                spans.append(dict(quote_sha256=c.digest(quote),occurrences=occurrences))
            record[key+'_spans']=spans
        public.append(record);private.append(dict(record,claim=d['claim'],decisive_quotes=decision['decisive_quotes'],counterevidence_quotes=decision['counterevidence_quotes']))
    if len(public)!=12:raise ValueError('Expected all12 kept-correct natural cases')
    c.putl(c.OUT/'semantic_A_kept.jsonl',public);c.putl(c.PRIVATE/'semantic_A_kept_quotes.jsonl',private)
    print(c.canonical(dict(reviewed=len(public),uncertain=sum(r['current_reference_sufficient']=='uncertain' for r in public),all_full_references_read=True,all_quotes_exact=True,paid_API=0)))

if __name__=='__main__':main()
