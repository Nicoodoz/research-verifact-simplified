"""GT-blind content reading only; no automatic per-case manual override."""
import common095 as c
if __name__=='__main__':
    inputs={r['id']:r for r in c.lines(c.PRIVATE/'screen_inputs.jsonl')}
    for i,v in enumerate(c.lines(c.PRIVATE/'pilot_checked.jsonl')):
        r=inputs[v['id']];print('\nCASE',i,v['id'],'OPERATED',v['operated']);print('ORIGINAL:',r['text'])
        if v['valid']:
            print('ATTRIBUTE:',v['attribute'],'EDIT:',repr(v['old_span']),'->',repr(v['new_span']));print('ALTERNATIVE:',v['alternative'])
            for a in v['anchors']:print('SOURCE',a['reference_id'],a['source_header'],'\n',a['quote'])
        else:print('PROGRAM STATUS',v.get('error'))
        print('CHECKER:',v['checker'])
