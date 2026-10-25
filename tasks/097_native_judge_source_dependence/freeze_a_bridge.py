"""Pre-outcome time bridge: fixed 12 historical C48-B requests, independent of accuracy."""
import common097 as c

def main():
    panel=c.lines(c.OUT/'a_execution_panel.jsonl');selected=sorted(panel,key=lambda r:c.digest('097/A/time_bridge/v1/'+r['id']))[:12]
    old_by_id={r['id']:r for r in c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl')}
    jobs=[];public=[]
    for r in selected:
        # Resolve exact prior body through 095 same-ID panel, no response labels used.
        old=old_by_id[r['id']]
        req=c.read(c.ROOT/old['B']['request_path']);body=req['job']['body'] if 'job' in req else req['body']
        assert body['model']==c.MODEL and body['enable_thinking'] is True and body['reasoning_effort']=='high' and body['max_tokens']==8192
        digest=c.digest(c.canonical(body));j=dict(id=r['id'],arm='C48_B_bridge',body=body,body_sha256=digest,reference_sha256=r['C48_sha256'],request_id=c.digest('097/A/time_bridge/v1/'+r['id'])[:28],bound_cny=((len(c.canonical(body).encode('utf-8'))+2000)*3+8192*9)/1e6)
        jobs.append(j);public.append(dict(id=r['id'],sid=r['sid'],body_sha256=digest,old_receipt_path=old['B']['receipt_path'],old_receipt_sha256=c.sha(c.ROOT/old['B']['receipt_path']),new_request_id=j['request_id']))
    c.write_lines(c.PRIVATE/'a_bridge_jobs.jsonl',jobs);c.write_lines(c.OUT/'a_bridge_freeze.jsonl',public)
    c.write_json(c.OUT/'a_bridge_plan.json',dict(N=12,patients=len({r['sid'] for r in selected}),selection='Fixed SHA256 097/A/time_bridge/v1/ID among frozen A160, before analysis and independent of old/new verdict',purpose='Nominally identical same snapshot body at current run time vs historical 095; diagnose temporal variation, not optimize primary A result',max_initial_bound_cny=sum(j['bound_cny'] for j in jobs),execution_condition='A 480 HTTP200 complete and shared operating cap 18.0 CNY remains sufficient including in-flight reservations',jobs_sha256=c.sha(c.PRIVATE/'a_bridge_jobs.jsonl'),new_API_requested=12))
    print('bridge frozen 12')
if __name__=='__main__':main()
