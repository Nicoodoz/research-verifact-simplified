"""Replay every frozen C48 pack and locate selected literal anchors in saved spans."""
from pathlib import Path
from collections import Counter
import re
import common018 as c
from diagnose018 import load_notes

TARGETS={'N180','N395','N526','N585','N642','S079','S092','S517','S575'}

def build(out):
    c.require(not out.exists(),'Trace exists')
    src,ps,paths=c.prior.sources();rows={r['proposition_id']:r for r in src}
    notes,mats,_=load_notes();replays=[];traces=[]
    for m in mats.values():
        item=rows[m['row']['proposition_id']]
        replay=c.prior.core.select_evidence(item['C48'],item['scores'],ps,item['admission'])
        for key in ('reference','selected_ids','body_characters'):
            c.require(replay[key]==item['baseline'][key],'C48 reconstruction mismatch')
        replays.append(dict(case_id=m['row']['case_id'],reference_sha256=c.prior.old.pilot.digest_text(replay['reference']),selected=len(replay['selected_ids']),first_skip_counts=dict(Counter(s['reason'] for s in replay['selection_skips']))))
        suffix=m['row']['case_id'].rsplit('_',1)[1]
        if suffix not in TARGETS:continue
        n=next(n for n in notes if n['case_id']==m['row']['case_id'])
        skips={s['passage_id']:s['reason'] for s in replay['selection_skips']}
        rank={a:{p:i+1 for i,(p,_) in enumerate(item['rankings'][a])} for a in ('dense','bm25')}
        rerank=sorted(item['C48'],key=lambda p:(-item['scores'][p],p))
        for a in n['anchors']:
            if a['arm']!='O' or a.get('kind')=='output' or len(a['quote'])<15:continue
            b=next(b for b in c.blocks(m['references']['O']) if b['number']==a['block'])
            pattern=re.compile(r'\s+'.join(re.escape(x) for x in a['quote'].split()),re.I)
            found=[]
            for pid,p in ps.items():
                if p['subject_id']!=item['subject_id'] or p['date']!=b['date']:continue
                for hit in pattern.finditer(p['text']):
                    found.append(dict(passage_id=pid,note_id=p['note_id'],note_sha256=p['note_sha256'],date=p['date'],time=p['time'],category=p['category'],description=p['description'],
                        start=p['start']+hit.start(),end_exclusive=p['start']+hit.end(),quote=hit.group(),passage_start=p['start'],passage_end=p['end_exclusive'],
                        dense_rank=rank['dense'].get(pid),bm25_rank=rank['bm25'].get(pid),C48_candidate_rank=item['C48'].index(pid)+1 if pid in item['C48'] else None,
                        C48_rerank_rank=rerank.index(pid)+1 if pid in rerank else None,score=item['scores'].get(pid),in_saved_scored_union=pid in item['wide'],
                        selected=pid in replay['selected_ids'],first_skip=skips.get(pid),disposition='selected' if pid in replay['selected_ids'] else skips.get(pid,'outside_C48_candidates')))
            traces.append(dict(case_id=n['case_id'],anchor=a,matched_passages=found,matching='same patient + date + whitespace-insensitive literal; no semantic absence inferred from zero matches',original_upstream='unavailable'))
    out.mkdir(parents=True);c.write_lines(out/'C48_replay.jsonl',replays);c.write_json(out/'anchor_traces.json',traces)
    c.write_json(out/'summary.json',dict(reconstructed=len(replays),target_cases=len(TARGETS),anchors=len(traces),matched=sum(bool(t['matched_passages']) for t in traces),not_retrieval_recall_or_causal_prevalence=True))
    c.seal(out,paths+[c.OUT/'preparation_001/manifest.json']+sorted(c.TASK.glob('notes_batch*.json')),[Path(__file__)])
    print(c.canonical(c.read(out/'summary.json')))
    for t in traces:print(t['case_id'],t['anchor']['quote'],[(x['C48_candidate_rank'],x['C48_rerank_rank'],x['dense_rank'],x['bm25_rank'],x['disposition']) for x in t['matched_passages']])

if __name__=='__main__':build(c.OUT/'trace_001')
