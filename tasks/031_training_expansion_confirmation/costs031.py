"""Usage/reservations and standalone role cost accounting, no new calls."""
from collections import defaultdict,Counter
import common031 as c
import api031 as a
def run(destination):
    out=c.OUT/destination;c.require(not out.exists(),'New cost report required');out.mkdir();attempts,terminal,exhausted=a.state();meta={r['proposition_id']:r for r in c.csvread(c.OUT/'planning_001/claim_metadata.csv')};roles=defaultdict(lambda:dict(attempts=0,http200=0,used_or_reserved_cny=0.,prompt_tokens=0,completion_tokens=0,unknown_reserved_cny=0.));ledger=[]
    for r in attempts:
        job=r['job'];group=meta[job['proposition_id']]['role'] if job.get('proposition_id') in meta else 'shared_BGE';role=job.get('role',job['kind']);request_path=c.ROOT/r['path'];rp=request_path.parent/'receipt.json';tr=c.read(rp)['transport'] if rp.exists() else {};usage={}
        if tr.get('body_text'):
            try:usage=c.api_plain_usage(tr) if hasattr(c,'api_plain_usage') else __import__('json').loads(tr['body_text']).get('usage',{})
            except (ValueError,TypeError):pass
        key=group+'/'+role;entry=roles[key];entry['attempts']+=1;entry['http200']+=r['http_status']==200;entry['used_or_reserved_cny']+=r['charge_cny'];entry['prompt_tokens']+=usage.get('prompt_tokens',0);entry['completion_tokens']+=usage.get('completion_tokens',0)
        if 'reservation' in r['charge_basis'] or 'unknown' in r['charge_basis']:entry['unknown_reserved_cny']+=r['charge_cny']
        ledger.append({k:v for k,v in r.items() if k!='job'}|dict(group=group,role=role))
    needed={'A':['score','peer'],'B':['score','peer','repeat'],'C':['score','peer','trace'],'D':['score','peer','repeat','trace']};standalone={}
    for group in ('expansion','confirmation'):
        standalone[group]={m:dict(roles=rr,requests=sum(roles[group+'/'+role]['attempts'] for role in rr),used_or_reserved_cny=sum(roles[group+'/'+role]['used_or_reserved_cny'] for role in rr),scope='Judge only at observed031 inputs/usage; BGE shared provisioning separate, not eight times duplicated') for m,rr in needed.items()}
    c.csvwrite(out/'ledger.csv',ledger);c.put(out/'costs.json',dict(total_used_or_reserved_cny=sum(r['charge_cny'] for r in attempts),cap_cny=80,roles=dict(roles),standalone=standalone,exhausted_accounts=sorted(exhausted),raw_attempts=len(attempts),HTTP200=len(terminal),price_basis='verified Beijing peak/no cache estimates; not invoice; unknown attempts retain byte upper bounds'));c.put(out/'manifest.json',dict(created_utc=c.now(),outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('cost ledger saved',sum(r['charge_cny'] for r in attempts))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',default='costs_001');run(p.parse_args().output)
