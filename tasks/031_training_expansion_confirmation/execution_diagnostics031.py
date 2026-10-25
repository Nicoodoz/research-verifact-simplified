"""Read saved execution records only; no GT and no API calls."""
from collections import Counter, defaultdict
import common031 as c
import api031 as a

def run(destination='execution_diagnostics_001'):
    out=c.OUT/destination;c.require(not out.exists(),'New diagnostic directory required')
    attempts,terminal,exhausted=a.state();meta={r['proposition_id']:r for r in c.csvread(c.OUT/'planning_001/claim_metadata.csv')}
    timing=defaultdict(list);hours=Counter();statuses=Counter();models=Counter();anomalies=[];failures=[]
    for row in attempts:
        request=c.read(c.ROOT/row['path']);job=row['job'];pid=job.get('proposition_id');group=meta.get(pid,{}).get('role','shared_BGE');role=job.get('role',job['kind']);when=request['created_utc'];timing[group+'/'+role].append(when);hours[when[:13],group,role]+=1
        if row['http_status']!=200:failures.append({k:v for k,v in row.items() if k!='job'})
    for rid,entry in terminal.items():
        parsed=entry['parsed'];role=entry['job'].get('role',entry['job']['kind']);statuses[role,parsed['status']]+=1;models[role,parsed.get('model_returned','not_reported')]+=1
        if parsed['status'] not in ('success','valid'):
            anomalies.append(dict(request_id=rid,role=role,receipt=entry['receipt'],status=parsed['status'],diagnostics={k:v for k,v in parsed.items() if k in ('errors','warnings','flags','format_anomalies','diagnostics')}))
    out.mkdir();c.csvwrite(out/'attempts_by_hour.csv',[dict(UTC_hour=h,group=g,role=r,attempts=n) for (h,g,r),n in sorted(hours.items())]);c.csvwrite(out/'failures_and_unknown.csv',failures);c.put(out/'format_anomalies.json',anomalies)
    c.put(out/'summary.json',dict(created_utc=c.now(),attempts=len(attempts),HTTP200=len(terminal),statuses=[dict(role=r,status=s,n=n) for (r,s),n in sorted(statuses.items())],returned_models=[dict(role=r,model=m,n=n) for (r,m),n in sorted(models.items())],timing={k:dict(first_utc=min(v),last_utc=max(v),attempts=len(v)) for k,v in timing.items()},exhausted_accounts=sorted(exhausted),note='401 skip explicitly authorized; neither401 nor429 implies exhausted credit; timestamps describe scheduling, not causal isolation'))
    c.put(out/'manifest.json',dict(inputs={str((c.TASK/'execution_diagnostics031.py').relative_to(c.ROOT)):c.sha(c.TASK/'execution_diagnostics031.py')},outputs={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('Saved execution diagnostics',len(attempts))

if __name__=='__main__':run()
