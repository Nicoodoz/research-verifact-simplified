"""Independent-of-display membership checks for every concrete add/loss statement."""
from pathlib import Path
import study013 as s
from prepare013 import source_data

SPECS=[
 ('N305','564761',637,'selector',True,True),('N425','470890',0,'wide_candidates',True,True),
 ('N644','471448',2549,'wide_candidates',True,True),('N147','400203',0,'selector',True,False),
 ('N153','400177',3191,'selector',True,False),('N182','626473',3824,'selector',False,True),
 ('N182','626507',1279,'selector',False,True),('N419','474420',1150,'wide_candidates',False,True),
 ('N073','375661',3192,'wide_candidates',True,False),('N501','473836',0,'selector',True,False),
 ('N367','565208',1264,'wide_candidates',False,True),('N367','565349',5157,'wide_candidates',False,True),
 ('N144','400215',5744,'selector',False,True),('N530','473395',1911,'selector',False,True),
 ('N627','469172',4456,'wide_candidates',False,True),('N395','564631',4504,'selector',False,True)]

def run(out=None):
    out=out or s.OUT/'membership_backcheck_001'
    _,pp,notes,_=source_data();inputs={x['case_id']:x for x in s.pilot.jsonl(s.OUT/'screen_inputs_001/inputs.jsonl')}
    values=[]
    for cid,nid,start,arm,expect_b,expect_a in SPECS:
        p=next(p for p in pp.values() if p['note_id']==nid and p['start']==start)
        assert p['subject_id']==inputs[cid]['subject_id'] and notes[nid]['TEXT'][start:p['end_exclusive']]==p['text']
        actual={a:p['passage_id'] in inputs[cid]['retrieval'][a]['selected_ids'] for a in ('baseline',arm)}
        assert actual=={'baseline':expect_b,arm:expect_a},(cid,actual)
        values.append(dict(case_id=cid,arm=arm,note_id=nid,start=start,end_exclusive=p['end_exclusive'],passage_id=p['passage_id'],
            raw_sha256=s.pilot.digest_text(notes[nid]['TEXT']),raw_text=p['text'],membership=actual,
            statement='retained_in_both' if expect_b and expect_a else 'removed' if expect_b else 'added'))
    out.mkdir(parents=True,exist_ok=False);s.pilot.write_json(out/'checks.json',values)
    s.freeze(out,[s.OUT/'screen_inputs_001/manifest.json'],[Path(__file__)])
    print('Membership assertions verified:',len(values))

if __name__=='__main__':run()
