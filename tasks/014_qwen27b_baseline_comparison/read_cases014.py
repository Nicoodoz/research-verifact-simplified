"""Display full cases, reusing only previously emitted byte-identical record contents.

Remove local ordinal solely for cache keys; preserve all metadata, raw layout and
whitespace. Emitted does not itself mean medically reviewed: case_notes is separate.
"""
import argparse
import re
import common014 as c

def split(reference):
    matches=list(re.finditer(r'(?m)^(\d+)\. (?=Date:)',reference))
    c.require(matches,'No reference records')
    head=reference[:matches[0].start()]
    blocks=[(m.group(1),reference[m.end():matches[i+1].start() if i+1<len(matches) else len(reference)]) for i,m in enumerate(matches)]
    c.require(head+''.join(n+'. '+t for n,t in blocks)==reference,'Reading reconstruction changed bytes')
    return head,blocks

def show(ids,seed=False):
    path=c.OUT/'reading_cache_001.json'
    cache=c.read(path) if path.exists() else {}
    for case in ids:
        packet=c.read(c.OUT/'analysis_001/cases'/(case+'.json'))
        head,blocks=split(packet['reference'])
        if not seed:
            print('\nCASE',case,c.canonical(packet['row']))
            print('CLAIM\n'+packet['claim']+'\nREFERENCE HEADER\n'+head)
        for n,t in blocks:
            key=c.fingerprint([packet['row']['subject_id'],t])
            if not seed:
                if key in cache:print(f'REFERENCE {n}: exact content already emitted at '+cache[key])
                else:print(f'REFERENCE {n}\n'+t)
            cache.setdefault(key,case+'/'+n)
        if not seed:
            print('V4 COMPLETE OUTPUT\n'+packet['v4_output'])
            print('QWEN COMPLETE OUTPUT\n'+packet['qwen_output'])
    c.save(path,cache)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='+');p.add_argument('--seed-already-read',action='store_true')
    a=p.parse_args();show(a.cases,a.seed_already_read)
