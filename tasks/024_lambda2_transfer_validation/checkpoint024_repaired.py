"""Save service/format-only checkpoint, without reading GT or computing performance."""
import argparse,json,subprocess
from collections import Counter
from pathlib import Path
import format024 as c
def run(name):
    c.require(not (c.OUT/'live.lock').exists(),'Runner active')
    jobs=c.verify_inputs();attempts,terminal=c.load_attempts(jobs)
    byid={j['request_id']:j for j in jobs};invalid=[]
    for rid,p in terminal.items():
        if p['status']=='success':continue
        duplicates=[]
        def pairs(items):
            seen={}
            for k,v in items:
                if k in seen:duplicates.append(dict(key=k,values_equal=seen[k]==v,value_type=type(v).__name__))
                seen[k]=v
            return seen
        try:json.loads(p.get('output_text') or '{}',object_pairs_hook=pairs)
        except ValueError:pass
        invalid.append(dict(request_id=rid,model_key=byid[rid]['model_key'],arm=byid[rid]['arm'],errors=p['errors'],duplicates=duplicates))
    out=c.OUT/name;out.mkdir(exist_ok=False)
    c.csvwrite(out/'attempt_costs.csv',attempts)
    c.put(out/'status.json',dict(created_utc=c.now(),planned_requests=len(jobs),attempts=len(attempts),http200=len(terminal),valid=sum(p['status']=='success' for p in terminal.values()),invalid=invalid,not_sent=len(jobs)-len({a['request_id'] for a in attempts}),occupied_cny=sum(a['charge_cny'] for a in attempts),unknown_reserved_cny=sum(a['charge_cny'] for a in attempts if a['charge_basis']!='peak_no_cache_usage_estimate'),cap_cny=80,coverage={f'{m}/{arm}':dict(planned=sum(j['model_key']==m and j['arm']==arm for j in jobs),http200=sum(j['model_key']==m and j['arm']==arm and j['request_id'] in terminal for j in jobs),valid=sum(j['model_key']==m and j['arm']==arm and j['request_id'] in terminal and terminal[j['request_id']]['status']=='success' for j in jobs)) for m in c.MODELS for arm in ('B','S')},effect_evaluation_performed=False,reserved_used=False,independent_audit=False))
    paths=list((c.OUT/'attempts').glob('*/*.json'))+list((c.OUT/'preparation_001').glob('*'))+list(c.TASK.glob('*.py'))+[c.OUT/'protocol_001.md']+list(out.glob('*'))
    c.put(out/'manifest.json',dict(git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in paths}))
    print(c.canonical(c.read(out/'status.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args();c.require('/' not in a.name and '\\' not in a.name and a.name.startswith('checkpoint_'),'Invalid checkpoint name');run(a.name)
