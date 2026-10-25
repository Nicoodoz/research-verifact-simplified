"""Zero-API B source recovery audit on non-A natural material; no method search."""
import re, statistics
from collections import Counter,defaultdict
import common097 as c
import sys
sys.path.insert(0,str(c.ROOT/'tasks/093_lossless_evidence_budget'))
from operation093 import parse

META=re.compile(r'^\d+\. Date: (?P<date>.*?), Time: (?P<time>.*?), Note Category: (?P<category>.*?), Note ID: (?P<note>.*?), Raw characters: \[(?P<start>\d+),(?P<end>\d+)\) \| Text:$')
CORPORA=[
 'outputs/009_retrieval_baselines/development_001/preparation/corpus.jsonl',
 'outputs/009_retrieval_baselines/confirmation_001/preparation/corpus.jsonl',
 'outputs/016_disagreement_triggered_review_validation/stage1/preparation_002/corpus.jsonl',
 'outputs/020_lambda2_patient_validation/new10/preparation_002/corpus.jsonl',
 'outputs/031_training_expansion_confirmation/materials_001/corpus.jsonl',
 'outputs/036_final_validation/materials_001/corpus.jsonl',
 '.local_models/092/missing_corpus.jsonl']

def main():
    used={r['id'] for r in c.lines(c.OUT/'a_execution_panel.jsonl')}
    natural=[r for r in c.lines(c.ROOT/'outputs/096_r1_native_priorg/main_panel.jsonl') if r['eligible'] and r['id'] not in used]
    inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl')}
    corpus={};by_note=defaultdict(list);sources={}
    for rel in CORPORA:
        p=c.ROOT/rel
        if not p.exists():continue
        sources[rel]=c.sha(p)
        for row in c.lines(p):
            if not all(k in row for k in ('note_id','start','end_exclusive','text')):continue
            key=(str(row['note_id']),int(row['start']),int(row['end_exclusive']),c.digest(row['text']))
            corpus.setdefault(key,row)
    for key,row in corpus.items():by_note[key[0]].append(row)
    for note,rr in by_note.items():rr.sort(key=lambda r:(int(r['start']),int(r['end_exclusive'])))
    audit=sorted(natural,key=lambda r:c.digest('097/B/source_audit/v1/'+r['id']))[:40]
    result=[]
    for item in audit:
        inp=inputs[item['id']];_,entries=parse(inp['reference']);mapped=0;missing=0;same_full=0;neighbor=0;lengths=[];examples=[]
        for entry in entries:
            header=entry['header'].rstrip();m=META.match(header)
            if m is None:missing+=1;continue
            key=(m['note'],int(m['start']),int(m['end']),c.digest(entry['text']))
            row=corpus.get(key)
            if row is None:missing+=1;continue
            assert str(row['subject_id'])==str(item['sid'])
            mapped+=1;same_full+=row['text']==entry['text'];lengths.append(len(entry['text']))
            others=by_note[m['note']];index=next(i for i,p in enumerate(others) if p is row)
            has_neighbor=any(0<=j<len(others) and (abs(int(others[j]['start'])-int(row['end_exclusive']))<=8 or abs(int(row['start'])-int(others[j]['end_exclusive']))<=8) for j in (index-1,index+1))
            neighbor+=has_neighbor
            if len(examples)<2:examples.append(dict(note_sha256=c.digest(m['note']),start=int(m['start']),end=int(m['end']),source_sha256=c.digest(entry['text']),neighbor=has_neighbor))
        result.append(dict(id=item['id'],sid=item['sid'],author=item['author'],GT=item['GT'],reference_sha256=c.digest(inp['reference']),entries=len(entries),mapped=mapped,missing=missing,already_full_paragraph=same_full,adjacent_source_candidates=neighbor,mean_entry_chars=statistics.mean(lengths) if lengths else None,source_examples=examples))
    # Remove any temptation to treat GT as construction input: audit split only.
    c.write_lines(c.OUT/'b_source_audit_40.jsonl',result)
    stats=dict(N=len(result),patients=len({r['sid'] for r in result}),entries=sum(r['entries'] for r in result),mapped=sum(r['mapped'] for r in result),missing=sum(r['missing'] for r in result),already_full_paragraph=sum(r['already_full_paragraph'] for r in result),adjacent_source_candidates=sum(r['adjacent_source_candidates'] for r in result),mapping_method='exact note ID, raw offset range, text SHA, same subject; candidate neighboring corpus spans are not automatically same clinical event',corpora_sha256=sources,audit_selection='40 natural 096 non-A IDs by fixed hash; includes GT/author only for description, not source matching',new_API=0)
    c.write_json(c.OUT/'b_source_audit_summary.json',stats);print({k:stats[k] for k in ('N','patients','entries','mapped','missing','already_full_paragraph','adjacent_source_candidates')})
if __name__=='__main__':main()
