import argparse
import common095 as c
import method095 as m
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('start',type=int);p.add_argument('stop',type=int);a=p.parse_args()
    rows=[r for r in c.lines(c.OUT/'construction_quality_sample.jsonl') if r['reviewer']=='root'];vv={r['id']:r for r in c.lines(c.PRIVATE/'checked.jsonl')};inputs={r['id']:r for r in c.lines(c.PRIVATE/'screen_inputs.jsonl')}
    for i in range(a.start,min(a.stop,len(rows))):
        r=rows[i];v=vv[r['id']];x=inputs[r['id']];refs=m.entries(x['reference']);print('\nCASE',i,r['id'],r['panel']);print('ORIGINAL',x['text']);print('EDIT',v['attribute'],repr(v['old_span']),'->',repr(v['new_span']));print('ALTERNATIVE',v['alternative'])
        for e in v['anchors']:print('ANCHOR',e['quote'],'\nCOMPLETE SOURCE ENTRY',refs[e['reference_id']])
