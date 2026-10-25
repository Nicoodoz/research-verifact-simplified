"""Emit complete case materials; cache only byte-identical already emitted record contents."""
import argparse
import common015 as c
from read_cases014 import split

def show(ids):
    path=c.OUT/'reading_cache_001.json';cache=c.read(path) if path.exists() else {}
    for cid in ids:
        p=c.read(c.OUT/'analysis_001/cases'/(cid+'.json'));head,blocks=split(p['reference'])
        print('\nCASE',cid,c.canonical(p['row']));print('CLAIM\n'+p['claim']+'\nREFERENCE HEADER\n'+head)
        for n,t in blocks:
            key=c.fingerprint([p['row']['subject_id'],t])
            print(f'REFERENCE {n}: exact content already emitted at '+cache[key] if key in cache else f'REFERENCE {n}\n'+t)
            cache.setdefault(key,cid+'/'+n)
        for field in ('v4_output','qwen_output','adjudication_output','evidence_only_output'):
            print(field+' COMPLETE\n'+p[field])
    c.save(path,cache)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='+');show(p.parse_args().cases)
