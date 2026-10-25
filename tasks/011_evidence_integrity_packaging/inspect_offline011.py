"""Deterministic pre-inference examples of actual source/packing differences."""
import study011 as s

if __name__=='__main__':
    folder=s.OUT/'offline_003';s.check(folder)
    views={v['passage_id']:v['views'] for v in s.pilot.jsonl(folder/'views.jsonl')}
    items=s.pilot.jsonl(folder/'inputs.jsonl')
    used={k for r in items for a in s.METHODS for k in r['retrieval'][a]['selected_ids']}
    chosen={}
    for kind in ('unique_note_test','enclosing_local_heading'):
        pool=[k for k in used if any(h['kind']==kind for h in views[k]['C']['source_context'])]
        for k in sorted(pool,key=lambda k:s.pilot.digest_text('011/offline/heading:'+k))[:12]:chosen.setdefault(k,[]).append(kind)
    for flag in ('left','right','unresolved'):
        pool=[k for k in used if (views[k]['B']['start']<views[k]['A']['start'] if flag=='left' else views[k]['B']['end_exclusive']>views[k]['A']['end_exclusive'] if flag=='right' else bool(views[k]['B']['repair']['unresolved']))]
        for k in sorted(pool,key=lambda k:s.pilot.digest_text('011/offline/boundary:'+flag+k))[:6]:chosen.setdefault(k,[]).append(flag)
    for r in items:
        if r['case_id'] not in ('N180','N642','N561'):continue
        for k in r['retrieval']['A']['selected_ids']:
            if views[k]['A']['note_id'] in ('90821','471448','1088126'):chosen.setdefault(k,[]).append(r['case_id'])
    out=s.OUT/'offline_review_003';out.mkdir()
    packets=[dict(index=i,passage_id=k,reasons=reasons,views=views[k]) for i,(k,reasons) in enumerate(sorted(chosen.items()),1)]
    s.pilot.write_jsonl(out/'packets.jsonl',packets)
    s.pilot.write_json(out/'summary.json',dict(examples=len(packets),selection='hash source-kind/boundary plus prior identity/condition probes; before any 011 Judge output'))
    s.seal(out,[folder/'manifest.json'],[s.TASK/'inspect_offline011.py'])
    print('Offline QC packets',len(packets))
