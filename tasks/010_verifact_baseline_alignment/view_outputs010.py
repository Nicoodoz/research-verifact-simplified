"""Display complete already-saved Judge outputs after final scoring."""
import sys
import alignment_common as s

if __name__=='__main__':
    cases=set(sys.argv[1:])
    for p in s.pilot.jsonl(s.OUT/'review_002/packets.jsonl'):
        r=p['row']
        if r['case_id'] not in cases:
            continue
        print('\nCASE',r['case_id'],r['author_type'],'GT',r['human_gt'],'old released',p['released_system_verdict'],'old C48',r['old_009_C48'])
        print(p['input']['text'])
        for arm,result in p['outputs'].items():
            print('FULL OUTPUT',arm,result['status'],result.get('verdict'))
            print(result.get('output_text'))
