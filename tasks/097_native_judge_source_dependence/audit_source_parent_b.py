"""Correct v1 granularity error: compare C48 passages with original note paragraphs."""
import csv,gzip,re,statistics,sys
from collections import Counter
import common097 as c
sys.path.insert(0,str(c.ROOT/'tasks/093_lossless_evidence_budget'))
from operation093 import parse
from audit_source_b import META

SEPARATOR=re.compile(r'\n[ \t\r]*\n')
ITEM=re.compile(r'(?m)^\s*(?:[-*•]|\d+[.)]|[A-Za-z][.)])\s+')
def parent_span(text,start,end):
    lo=0
    for m in SEPARATOR.finditer(text):
        hi=m.start()
        if start>=lo and end<=hi:return lo,hi
        lo=m.end()
    assert start>=lo and end<=len(text)
    return lo,len(text)
def main():
    rows=c.lines(c.OUT/'b_source_audit_40.jsonl');ids={r['id'] for r in rows}
    inputs={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl') if r['proposition_id'] in ids}
    wanted=set()
    for x in inputs.values():
        _,es=parse(x['reference'])
        for e in es:wanted.add(META.match(e['header'].rstrip())['note'])
    source=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz';notes={}
    with gzip.open(source,'rt',encoding='utf-8-sig',newline='') as f:
        for r in csv.DictReader(f):
            if r['ROW_ID'] in wanted:notes[r['ROW_ID']]=r
    assert set(notes)==wanted
    out=[];summary=Counter();parent_lengths=[]
    for row in rows:
        pid=row['id'];x=inputs[pid];_,entries=parse(x['reference'])
        for i,e in enumerate(entries,1):
            m=META.match(e['header'].rstrip());note=notes[m['note']];raw=note['TEXT'];start,end=int(m['start']),int(m['end'])
            assert raw[start:end]==e['text'] and str(int(note['SUBJECT_ID']))==row['sid']
            lo,hi=parent_span(raw,start,end)
            # Parent delimiters trim whitespace; comparison remains raw-character exact.
            while lo<hi and raw[lo].isspace():lo+=1
            while hi>lo and raw[hi-1].isspace():hi-=1
            parent=raw[lo:hi];assert lo<=start<end<=hi
            full=(lo==start and hi==end);extra=(start-lo)+(hi-end)
            items=len(ITEM.findall(parent));cross_item_risk=items>1
            out.append(dict(id=pid,entry=i,note_id_sha256=c.digest(m['note']),note_sha256=c.digest(raw),source_range=[start,end],parent_range=[lo,hi],source_sha256=c.digest(e['text']),parent_sha256=c.digest(parent),source_chars=end-start,parent_chars=len(parent),extra_parent_chars=extra,already_full_parent=full,item_markers=items,cross_item_risk=cross_item_risk,source_note_date=note['CHARTDATE'][:10]))
            summary['entries']+=1;summary['full_parent']+=full;summary['cut_parent']+=not full;summary['cross_item_risk']+=cross_item_risk;summary['extra_parent_chars']+=extra;parent_lengths.append(len(parent))
    c.write_lines(c.OUT/'b_source_parent_audit_40.jsonl',out)
    c.write_json(c.OUT/'b_source_parent_summary.json',dict(**summary,N_cases=len(rows),N_notes=len(notes),parent_length_mean=statistics.mean(parent_lengths),parent_length_max=max(parent_lengths),all_raw_slices_verified=True,source_sha256=c.sha(source),correction='v1 field already_full_paragraph was mislabeled: it tested saved passage equality only. This v2 compares the actual raw note paragraph before 640-character passage splitting. v1 retained for audit.',GT_used_for_mapping=False,new_API=0))
    print(dict(summary),'notes',len(notes),'max parent',max(parent_lengths))
if __name__=='__main__':main()
