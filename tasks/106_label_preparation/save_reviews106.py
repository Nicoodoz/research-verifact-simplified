"""Validate authored source-review pointers and separate public hashes/private text."""
import argparse
import common106 as c


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--notes',default='semantic_A_natural_notes.json')
    a=p.parse_args()
    notes=c.read(c.OUT/a.notes)
    dossiers={r['id']:r for r in c.rows(c.PRIVATE/'A_source_review_dossiers.jsonl')}
    public=[];private=[]
    for note in notes:
        row=dossiers[note['id']]
        record={k:v for k,v in note.items() if not k.endswith('_ranges')}
        record.update({k:row[k] for k in ('sid','panel','GT','before','after','groups','reference_sha256','claim_sha256')})
        refs=[];quotes=[]
        for kind in ('decisive','counterevidence'):
            for start,end in note[kind+'_ranges']:
                assert 0 <= start < end <= len(row['full_reference'])
                excerpt=row['full_reference'][start:end]
                refs.append(dict(kind=kind,start=start,end=end,sha256=c.digest(excerpt)))
                quotes.append(dict(kind=kind,start=start,end=end,exact_text=excerpt))
        record['source_spans']=refs
        record['not_doctor_adjudication']=True
        record['model_internal_reason_not_observed']=True
        public.append(record)
        private.append(dict(record,claim=row['claim'],source_quotes=quotes))
    c.putl(c.OUT/'semantic_A_natural.jsonl',public)
    c.putl(c.PRIVATE/'semantic_A_natural_private.jsonl',private)
    print(c.canonical(dict(N=len(public),source_pointers_verified=True)))


if __name__=='__main__':main()
