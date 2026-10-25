"""Offline integrity probe, not a deployed H method or a classification test."""
import csv,gzip,re,statistics
from collections import Counter,defaultdict
import common097 as c

def main():
    src=c.ROOT/'data/00_raw/verifact-bhc/1.1.0/reference_ehr/ehr_noteevents.csv.gz'
    # Join only by full note hash and raw range from the audited 40 cases.
    audited=c.lines(c.OUT/'b_source_parent_audit_40.jsonl')
    hashes={r['note_sha256'] for r in audited};notes={}
    with gzip.open(src,'rt',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            h=c.digest(row['TEXT'])
            if h in hashes:notes[h]=row['TEXT']
    assert len(notes)==len(hashes)
    info=[];case=defaultdict(list)
    for r in audited:
        raw=notes[r['note_sha256']];a,b=r['source_range'];p,q=r['parent_range']
        # Nearest physical line boundaries inside the original paragraph. A line is not asserted to be one event.
        left=max(p,raw.rfind('\n',p,a)+1)
        right=raw.find('\n',b,q)
        if right<0:right=q
        while left<a and raw[left].isspace():left+=1
        while right>b and raw[right-1].isspace():right-=1
        assert p<=left<=a<b<=right<=q and raw[a:b]
        extra=(a-left)+(right-b)
        safe=extra>0 and extra<=400 and right-left<=1000
        case[r['id']].append((r,safe,extra))
        info.append(dict(id=r['id'],entry=r['entry'],source_range=[a,b],candidate_line_range=[left,right],candidate_sha256=c.digest(raw[left:right]),extra_chars=extra,trigger=safe,reason='same physical line, <=400 extra, <=1000 total' if safe else 'no_cut_or_budget_limit',contains_original=raw[a:b] in raw[left:right],crosses_paragraph=False,semantic_dependency_confirmed=False))
    original={r['proposition_id']:r for r in c.lines(c.ROOT/'.local_models/092/inputs.jsonl') if r['proposition_id'] in case}
    per=[]
    for pid,rr in case.items():
        added=sum(extra for _,safe,extra in rr if safe)
        per.append(dict(id=pid,entries=len(rr),safe_line_triggers=sum(safe for _,safe,_ in rr),added_chars_if_all_safe=added,baseline_chars=len(original[pid]['reference']),would_exceed_8000_reference_chars=len(original[pid]['reference'])+added>8000))
    c.write_lines(c.OUT/'b_line_probe_entries.jsonl',info)
    c.write_lines(c.OUT/'b_line_probe_cases.jsonl',per)
    summary=dict(N_cases=len(per),N_entries=len(info),trigger_entries=sum(r['trigger'] for r in info),trigger_cases=sum(r['safe_line_triggers']>0 for r in per),cases_exceeding_8000_if_all_applied=sum(r['would_exceed_8000_reference_chars'] for r in per),mean_extra_for_triggers=statistics.mean(r['extra_chars'] for r in info if r['trigger']) if any(r['trigger'] for r in info) else 0,all_contain_source=all(r['contains_original'] for r in info),semantic_dependency_confirmed=False,method_frozen=False,classification_API=0,interpretation='Only a source-span integrity probe. Physical line boundary is not a clinical event/list-item dependency; no H representation or F/H matched comparator was frozen.')
    c.write_json(c.OUT/'b_line_probe_summary.json',summary);print(summary)
if __name__=='__main__':main()
