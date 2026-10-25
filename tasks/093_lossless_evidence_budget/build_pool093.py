"""GT-blind fixed-budget additions using existing native 031 D48/rerank traces."""
from collections import Counter
import json
import common093 as c
from operation093 import factor,encode_with_dictionary,parse
def display(i,p):
    return f"{i}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}"
def render(prefix,ids,corpus):
    ids=sorted(ids,key=lambda i:(corpus[i]['date'],corpus[i]['time'],corpus[i]['note_id'],corpus[i]['start']))
    return prefix+'\n'.join(display(i+1,corpus[pid]) for i,pid in enumerate(ids))
def main():
    base=c.ROOT/'outputs/031_training_expansion_confirmation'
    cases=c.lines(c.ROOT/'outputs/042_coverage_aware_evidence_packing/planning_001/selector_outputs.jsonl')
    corpus={r['passage_id']:r for r in c.lines(base/'materials_001/corpus.jsonl')}
    candidates={r['proposition_id']:r['candidate_ids']['C48'] for r in c.lines(base/'retrieval_001/candidates.jsonl')}
    jobs={r['request_id']:r for r in c.lines(base/'retrieval_001/jobs.jsonl') if r['proposition_id'] in {x['id'] for x in cases}}
    scores={}
    for path in sorted((base/'attempts').glob('*/request.json')):
        req=c.read(path);rid=req['job']['request_id']
        if rid not in jobs:continue
        receipt=path.parent/'receipt.json'
        if not receipt.exists():continue
        tr=c.read(receipt)['transport']
        if tr['http_status']!=200:continue
        assert rid not in scores
        raw=json.loads(tr['body_text']);job=jobs[rid]
        scores[rid]={job['passage_ids'][z['index']]:float(z['relevance_score']) for z in raw['results']}
    byid={j['proposition_id']:scores[rid] for rid,j in jobs.items()}
    pub=[];private=[]
    for row in cases:
        pid=row['id'];original=row['baseline_reference'];prefix,_=parse(original);ids=list(row['baseline_ids'])
        assert render(prefix,ids,corpus)==original
        f=factor(original);extra=[];current=f['reference'];note_counts=Counter(corpus[i]['note_id'] for i in ids);texts={corpus[i]['text'] for i in ids}
        assert set(candidates[pid])<=set(byid[pid])
        if f['saved']:
            for candidate in sorted(candidates[pid],key=lambda i:(-byid[pid][i],i)):
                p=corpus[candidate]
                if candidate in ids or p['text'] in texts or note_counts[p['note_id']]>=2 or len(ids)+len(extra)>=16:continue
                raw=render(prefix,ids+extra+[candidate],corpus);trial,_=encode_with_dictionary(raw,f['dictionary'])
                if len(trial)>len(original):continue
                extra.append(candidate);note_counts[p['note_id']]+=1;texts.add(p['text']);current=trial
        assert len(current)<=len(original) and len(f['reference'])<=len(original)
        raw=render(prefix,ids+extra,corpus)
        _,encoded_body=encode_with_dictionary(raw,f['dictionary'])
        for key,text in f['dictionary'].items():encoded_body=encoded_body.replace(key,text)
        assert encoded_body==raw
        records=[dict(passage_id=i,note_id=corpus[i]['note_id'],start=corpus[i]['start'],end=corpus[i]['end_exclusive'],text_sha256=c.h(corpus[i]['text'])) for i in ids+extra]
        pub.append(dict(id=pid,sid=str(row['sid']),author=row['author'],original_source='031_native_C48',B_sha256=c.h(original),F_sha256=c.h(f['reference']),A_sha256=c.h(current),B_chars=len(original),F_chars=len(f['reference']),A_chars=len(current),F_changed=f['saved']>0,A_added=len(extra),A_changed=current!=original,baseline_ids=ids,added_ids=extra,source_records=records,roundtrip=True))
        private.append(dict(id=pid,sid=str(row['sid']),author=row['author'],claim=row['claim'],B=original,F=f['reference'],A=current))
    c.putl(c.OUT/'pool_operations.jsonl',pub);c.putl(c.PRIVATE/'pool_inputs.jsonl',private)
    changed=[r for r in pub if r['A_added']>0]
    c.put(c.OUT/'pool_summary.json',dict(N=len(pub),patients=len({r['sid'] for r in pub}),foldable=sum(r['F_changed'] for r in pub),actual_additions=len(changed),affected_patients=len({r['sid'] for r in changed}),total_added_passages=sum(r['A_added'] for r in changed),feasibility_pass=len(changed)>=12 and len({r['sid'] for r in changed})>=4,GT_read=False,API_calls=0,operation_sha256=c.sha(c.TASK/'operation093.py'),note='Refactor only: exact same whole-text factoring rule as inventory; encode helper extracted, no threshold change.'))
    print(c.read(c.OUT/'pool_summary.json'))
if __name__=='__main__':main()
