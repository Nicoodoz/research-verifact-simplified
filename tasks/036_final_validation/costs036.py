"""Full cumulative cost/coverage accounting and standalone method marginal costs."""
from collections import Counter,defaultdict
import common036 as c
import api036 as a
def main():
    out=c.OUT/'accounting_001';assert not out.exists();attempts,terminal,exhausted=a.state();totals=defaultdict(lambda:dict(attempts=0,received200=0,used_or_reserved_cny=0.,unknown_reserved_cny=0.,prompt_tokens=0,completion_tokens=0));raw=[]
    for x in attempts:
        role=x['role'];rn=x['job'].get('round','shared');v=totals[rn+'/'+role];v['attempts']+=1;v['received200']+=x['http_status']==200;v['used_or_reserved_cny']+=x['charge_cny']
        if 'reserv' in x['charge_basis']:v['unknown_reserved_cny']+=x['charge_cny']
        raw.append({k:v for k,v in x.items() if k!='job'})
    for t in terminal.values():
        j=t['job'];v=totals[j.get('round','shared')+'/'+j.get('role',j['kind'])]
        import json
        try:u=json.loads(t['transport']['body_text']).get('usage',{})
        except (ValueError,TypeError):u={}
        v['prompt_tokens']+=u.get('prompt_tokens',u.get('total_tokens',0) if j['kind']!='chat' else 0);v['completion_tokens']+=u.get('completion_tokens',0)
    rowcounts=c.read(c.OUT/'planning_001/counts.json');r0score=totals['R0/score']['used_or_reserved_cny'];q=totals['R0/peer']['used_or_reserved_cny'];bge=sum(v['used_or_reserved_cny'] for k,v in totals.items() if k.startswith('shared/'));b=totals['R0/baseline']['used_or_reserved_cny'];unit=[]
    for method,roles,amount in [('B','BGE + direct Judge',bge+b),('U0/U2/U2_T/standard controls','BGE + scoring (all controls share scoring)',bge+r0score),('U2+A Gate','BGE + scoring + candidate-only Qwen',bge+r0score+q)]:unit.append(dict(method=method,required_roles=roles,claims=rowcounts['n'],R0_estimated_cny=amount,estimated_cny_per_claim=amount/rowcounts['n'],Qwen_extra_cny=q if 'Gate' in method else 0.,offline_fit_cost_excluded=True))
    c.csvwrite(out/'ledger.csv',raw);c.csvwrite(out/'roles.csv',[dict(role=k,**v) for k,v in totals.items()]);c.csvwrite(out/'standalone_costs.csv',unit)
    statuses=Counter(t['parsed']['status'] for t in terminal.values());models=Counter(t['parsed'].get('model_returned','not_reported') for t in terminal.values() if t['job']['kind']=='chat')
    total=sum(x['charge_cny'] for x in attempts);assert total<=150
    c.put(out/'summary.json',dict(created_utc=c.now(),total_used_or_reserved_cny=total,unknown_reserved_cny=sum(v['unknown_reserved_cny'] for v in totals.values()),cap_cny=150,all_attempts=len(attempts),terminal_HTTP200=len(terminal),statuses=dict(statuses),returned_models=dict(models),exhausted_accounts=sorted(exhausted),supplier_invoices_reconciled=False,pricing='Peak no-cache public prices plus unknown reservations; not an invoice',role_summary=dict(totals)))
    c.put(out/'manifest.json',{p.name:c.sha(p) for p in out.iterdir() if p.is_file()})
    c.put(c.OUT/'execution_status.json',dict(state='api_completed',stage='all',completed_this_call=len(attempts),pending=0,inflight=0,used_cny=total,inflight_reserved_cny=0.,exhausted_accounts=sorted(exhausted),reason=None,updated_utc=c.now()))
    print('036 total used/reserved CNY',total)
if __name__=='__main__':main()
