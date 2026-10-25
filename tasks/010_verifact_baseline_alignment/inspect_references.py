"""All-reference structural/literal provenance diagnostics, not clinical relevance gold."""
from pathlib import Path
from collections import defaultdict,Counter
import re
import statistics
import alignment_common as s


def normalized(text):
    return re.sub(r'\s+',' ',text).strip()

def blocks(reference):
    marks=list(re.finditer(r'(?m)^(\d+)\. Date: ',reference))
    result=[]
    for i,m in enumerate(marks):
        end=marks[i+1].start() if i+1<len(marks) else len(reference)
        full=reference[m.start():end]
        meta,sep,text=full.partition(' | Text: ')
        assert sep,'Unrecognized reference block'
        def field(key):
            v=re.search(re.escape(key)+r': (.*?)(?=, (?:Time|Note Category|Note Description|Note ID|Raw characters):|$)',meta)
            return v.group(1) if v else None
        result.append(dict(number=int(m.group(1)),start=m.start(),end_exclusive=end,text_start=m.start()+len(meta)+len(sep),
            date=field('Date'),time=field('Time'),category=field('Note Category'),description=field('Note Description'),note_id=field('Note ID'),text=text.rstrip(),raw_block=full))
    assert [r['number'] for r in result]==s.pilot.reference_numbers(reference)
    return result


def inspect():
    prep=s.OUT/'preparation_001'
    s.check(prep)
    inputs=s.pilot.jsonl(prep/'inputs.jsonl')
    patients={x['subject_id'] for x in inputs}
    notes=s.pilot.subset_csv(s.RAW/'reference_ehr/ehr_noteevents.csv.gz','SUBJECT_ID',patients)
    bymeta=defaultdict(list)
    notes_by_id={n['ROW_ID']:n for n in notes}
    for n in notes:
        bymeta[(s.pilot.integer_id(n['SUBJECT_ID']),n['CHARTDATE'][:10],n['CATEGORY'])].append((n['ROW_ID'],normalized(n['TEXT'])))
    rows,allblocks,parsed=[],[],{}
    for item in inputs:
        for arm,ref in item['references'].items():
            bb=blocks(ref)
            parsed[(item['case_id'],arm)]=bb
            unique,possible=set(),set()
            unmatch,multi=0,0
            for b in bb:
                text=normalized(b['text'])
                matches=[nid for nid,raw in bymeta[(item['subject_id'],b['date'],b['category'])] if text and text in raw]
                if b['note_id']:
                    assert b['note_id'] in matches,'C48 raw block does not match its explicit note'
                    matches=[b['note_id']]
                if len(matches)==1:
                    unique.update(matches)
                if len(matches)>1:
                    multi+=1
                if not matches:
                    unmatch+=1
                possible.update(matches)
                allblocks.append(dict(case_id=item['case_id'],proposition_id=item['proposition_id'],subject_id=item['subject_id'],arm=arm,**b,
                    literal_matching_note_ids=matches,provenance_kind='explicit_id' if b['note_id'] else 'unique_literal' if len(matches)==1 else 'ambiguous_literal' if matches else 'unresolved_literal',
                    not_gold_evidence=True))
            rows.append(dict(case_id=item['case_id'],proposition_id=item['proposition_id'],subject_id=item['subject_id'],author_type=item['author_type'],arm=arm,
                reference_characters=len(ref),clinical_text_characters=sum(len(b['text']) for b in bb),blocks=len(bb),
                dates=len({b['date'] for b in bb}),earliest=min(b['date'] for b in bb),latest=max(b['date'] for b in bb),
                explicit_note_ids=len({b['note_id'] for b in bb if b['note_id']}),unique_literal_notes=len(unique),possible_note_union=len(possible),
                unresolved_blocks=unmatch,ambiguous_blocks=multi,blocks_with_description=sum(b['description'] is not None for b in bb),
                tiny_blocks=sum(len(b['text'].strip())<40 for b in bb),empty_blocks=sum(not b['text'].strip() for b in bb),
                heading_only=sum(len(b['text'].splitlines())==1 and b['text'].rstrip().endswith(':') for b in bb),
                duplicate_literal_blocks=len(bb)-len({(b['date'],normalized(b['text'])) for b in bb})))
    anchors=[]
    old=s.read_json(s.PRIOR/'review_002/semantic_001/anchors.json')
    for anchor in old:
        if anchor['kind']!='ehr':
            continue
        quote=normalized(anchor['quote'])
        hits={arm:[b['number'] for b in parsed[(anchor['case_id'],arm)] if quote in normalized(b['text'])] for arm in s.METHODS}
        anchors.append(dict(case_id=anchor['case_id'],quote=anchor['quote'],source_note_id=anchor['note_id'],source_start=anchor['start'],source_date=anchor['date'],
            hits=hits,note='literal quote diagnostic, not a medical recall denominator or proof of same event'))
    summary={arm:{field:statistics.mean(r[field] for r in rows if r['arm']==arm) for field in ('reference_characters','clinical_text_characters','blocks','dates','explicit_note_ids','unique_literal_notes','possible_note_union','unresolved_blocks','ambiguous_blocks','blocks_with_description','tiny_blocks','heading_only','duplicate_literal_blocks')} for arm in s.METHODS}
    out=s.OUT/'reference_diagnostics_001'
    out.mkdir(exist_ok=False)
    s.pilot.write_jsonl(out/'blocks.jsonl',allblocks)
    s.pilot.write_csv(out/'reference_features.csv',rows)
    s.pilot.write_json(out/'009_anchor_lookup.json',anchors)
    s.pilot.write_json(out/'summary.json',dict(by_arm_means=summary,claims=650,all_reference_blocks=len(allblocks),anchors=len(anchors),not_gold=True,
        note_coverage_caveat='VF lacks explicit note IDs; literal candidate sets are partial provenance, not exact clinical note coverage'))
    s.seal(out,[prep/'manifest.json',s.RAW/'reference_ehr/ehr_noteevents.csv.gz',s.PRIOR/'review_002/semantic_001/manifest.json'],[Path(__file__)])
    print(s.pilot.canonical(summary))


if __name__=='__main__':
    inspect()
