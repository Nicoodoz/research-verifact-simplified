"""Bounded lexical backchecks, never a clinical absence or relevance classifier."""
import argparse,re
from pathlib import Path
import study012 as s
from evidence012 import trace

QUERIES={
 'N050':r'coumadin|warfarin', 'N077':r'\bCRI\b|\bCKD\b|nephrop|renal.{0,35}diabet|diabet.{0,35}renal',
 'N086':r'No\s+nausea|\bN/V\b', 'N095':r'kcl|potassium',
 'N104':r'5\s*(?:lit|L\b)|rehydrat', 'N114':r'5\s*(?:lit|L\b)|returned to baseline',
 'N121':r'ambulat|walk|exert|activity', 'N139':r'returned to baseline|\bVSS\b',
 'N182':r'teach|educat|medication\s+list|anxi', 'N186':r'Promus|post.?dilat|3\.5\s*[xX*]\s*15|4\.0',
 'N188':r'angiogra|\bCTA\b|dissection', 'N220':r'plan|monitor',
 'N249':r'lexapro|escitalopram|SSRI', 'N262':r'psych', 'N264':r'enteric',
 'N282':r'intention|suicid|decided to|50\s*ASA|tylenol', 'N359':r'lopressor|diltiazem|dilt\s*g',
 'N385':r'return.{0,90}TSICU|rapid\s*afib|focus|pain management',
 'N388':r'pulm|pulmon|focus', 'N395':r'ortho',
 'N501':r'f/u\s*CT|follow.?up.{0,30}CT|Abdominal CT|CT.{0,30}contrast',
 'N526':r'tachycard|HR:\s*110\s*\(92', 'N578':r'low\s*U/?O|low\s*uop|marginal\s*uop|lasix',
 'N601':r'\bARDS\b|acute\s+respiratory\s+distress\s+syndrome',
}

def run(out):
    s.check(s.OUT/'materials_001')
    packets=s.pilot.jsonl(s.OUT/'materials_001/packets.jsonl')
    notes=s.pilot.jsonl(s.OUT/'materials_001/ehr_notes.jsonl')
    corpus=s.pilot.jsonl(s.OUT/'materials_001/corpus.jsonl')
    indexed={p['note_id'] for p in corpus}
    rows=[];summary=[]
    for p in packets:
        cid=p['row']['case_id'];sid=p['row']['subject_id'];rx=re.compile(QUERIES[cid],re.I)
        matched=[];scope=[n for n in notes if n['SUBJECT_ID']==sid]
        for n in scope:
            for m in rx.finditer(n['TEXT']):
                lo=max(0,m.start()-180);hi=min(len(n['TEXT']),m.end()+260)
                matched.append(dict(case_id=cid,note_id=n['ROW_ID'],subject_id=sid,match=[m.start(),m.end()],
                    window=[lo,hi],text=n['TEXT'][lo:hi],raw_sha256=s.pilot.digest_text(n['TEXT']),
                    chartdate=n['CHARTDATE'],charttime=n['CHARTTIME'],description=n['DESCRIPTION'],
                    in_C_index=n['ROW_ID'] in indexed,semantic_review='search_hit_only_not_evidence_judgment'))
        rows.extend(matched)
        summary.append(dict(case_id=cid,regex=QUERIES[cid],notes_searched=len(scope),matches=len(matched),
            matched_notes=len({m['note_id'] for m in matched}),zero_hits_is_not_absence=True))
    # Explicit diagnostic anchors chosen after fixed-case full reading; not retrieval gold.
    anchor_specs=[('N086',375697,'No nausea'),('N395',564621,'Consults:'),('N395',564631,'Consults:'),
        ('N359',564759,'Lopressor 5mg'),('N385',564759,'rapid afib'),
        ('N501',473836,'Abdominal CT'),('N578',470821,'Renal: low U/O')]
    nn={n['ROW_ID']:n for n in notes};pp={p['row']['case_id']:p for p in packets};anchors=[]
    for cid,nid,q in anchor_specs:
        n=nn[str(nid)];m=re.search(re.escape(q),n['TEXT'],re.I)
        assert m,(cid,nid,q)
        lo=m.start();hi=min(len(n['TEXT']),m.end()+160)
        anchors.append(dict(case_id=cid,search=q,trace=trace(pp[cid]['C_pipeline'],corpus,n,lo,hi)))
    out.mkdir(parents=True,exist_ok=False)
    s.pilot.write_jsonl(out/'matches.jsonl',rows);s.pilot.write_json(out/'summary.json',summary)
    s.pilot.write_json(out/'anchors.json',anchors)
    s.seal(out,[s.OUT/'materials_001/manifest.json'],[Path(__file__),s.TASK/'evidence012.py'])
    print(s.pilot.canonical(summary))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,default=s.OUT/'raw_search_001')
    run(ap.parse_args().output)
