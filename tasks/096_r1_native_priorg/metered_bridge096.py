"""Optional exact-input48 bridge only; disabled until separate API authorization.

Never replaces the095 primary cache; all requests are in this task's own ledger.
"""
import argparse,json,time,sys,sqlite3,os
import common096 as c
def reconcile_api(db,charge):
    for rq in (c.PRIVATE/'metered_attempts').glob('*/*/request.json'):
        request=c.read(rq);j=request['job'];n=request['attempt'];receipt=rq.parent/'receipt.json';tr=None
        if receipt.exists():
            rec=c.read(receipt);assert rec['request_sha256']==c.sha(rq);tr=rec['transport']
        status=tr.get('http_status') if tr else None;amount=charge(j,tr) if tr else j['bound_cny']
        db.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?)',(j['request_id'],n,amount,status,str(rq.parent.relative_to(c.ROOT)) if rq.parent.is_relative_to(c.ROOT) else str(rq.parent)))
    db.commit()

def run_unlocked(path):
    cfg=c.read(path);assert cfg.get('execute_metered_api_authorized') is True,'No metered API authorization'
    assert (c.OUT/'R1_INFERENCE_DONE.json').exists(),'Save R1 and notify GPU shutdown first'
    cap=cfg['metered_api_cap_cny'];assert isinstance(cap,(int,float)) and cap>0
    price=c.read(cfg['pricing_confirmation_path']);assert price['model']=='deepseek-v4-flash-0731' and price['region']=='cn-beijing' and price['verified_for_this_execution'] is True
    assert price['busy_rates']==[3,9,.3] and price['idle_rates']==[1.5,4.5,.15],'Rates changed; re-estimate before sending'
    sys.path.insert(0,str(c.ROOT/'tasks/024_lambda2_transfer_validation'));sys.path.insert(0,str(c.ROOT/'tasks/095_anchored_minimal_contrast'))
    from transport_direct024 import DirectClient
    from verifact_research.inference.aliyun import load_config,Config
    from pricing095_v3 import charge
    conf=load_config(c.ROOT/'.env.aliyun');assert '.cn-beijing.maas.aliyuncs.com/' in conf.endpoint
    client=DirectClient(Config(conf.api_key,conf.base_url,'deepseek-v4-flash-0731'),timeout=240)
    plan=c.read(c.OUT/'live_plan_selection.json')['name'];ids=set(c.read(c.OUT/'v4_bridge_variants.json')[plan]);jobs=[j for j in c.lines(c.PRIVATE/'v4_bridge_jobs.jsonl') if j['id'] in ids]
    frozen={r['request_id']:r for r in c.lines(c.OUT/'v4_bridge_request_manifest.jsonl')}
    for j in jobs:
        assert c.digest(j['body'])==j['body_sha256']==frozen[j['request_id']]['body_sha256']
        assert j['bound_cny']==frozen[j['request_id']]['bound_cny']
    db=sqlite3.connect(c.PRIVATE/'api_budget.sqlite',timeout=60);db.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT,n INT,charge REAL,status INT,path TEXT,PRIMARY KEY(rid,n))');db.commit()
    reconcile_api(db,charge)
    for j in jobs:
        while True:
            db.execute('BEGIN IMMEDIATE');old=db.execute('SELECT n,status FROM attempts WHERE rid=? ORDER BY n',(j['request_id'],)).fetchall()
            if any(s==200 for _,s in old):db.rollback();break
            n=max([i for i,_ in old],default=0)+1
            if n>3:db.rollback();raise RuntimeError('finite retries exhausted')
            used=db.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0]
            if used+j['bound_cny']>cap:db.rollback();raise RuntimeError('shared096 metered cap before send')
            folder=c.PRIVATE/'metered_attempts'/j['request_id']/str(n);folder.mkdir(parents=True,exist_ok=False)
            c.put(folder/'request.json',dict(job=j,attempt=n,prior_total=used,total_cap_cny=cap));db.execute('INSERT INTO attempts VALUES(?,?,?,?,?)',(j['request_id'],n,j['bound_cny'],None,str(folder.relative_to(c.ROOT))));db.commit()
            try:tr=client.send(j['body'])
            except Exception as e:tr=dict(http_status=0,outcome_unknown=True,body_text='',error_type=type(e).__name__)
            c.put(folder/'receipt.json',dict(transport=tr,request_sha256=c.sha(folder/'request.json')));amount=charge(j,tr);status=tr.get('http_status',0);db.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND n=?',(amount,status,j['request_id'],n));db.commit()
            if status==200:
                try:native=json.loads(tr['body_text'])
                except (ValueError,TypeError):native={}
                if isinstance(native,dict) and native.get('model') not in (None,'deepseek-v4-flash-0731'):raise RuntimeError('Successful wrong-model response retained; stop, do not retry')
                break
            if status not in {0,408,429,500,502,503,504}:raise RuntimeError('persistent service condition')
            time.sleep(min(2**n,8))
    db.close();print('V4_BRIDGE_SAVED — separate diagnostic only,095 primary unchanged')
def run(path):
    lock=c.PRIVATE/'metered_run.lock';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:run_unlocked(path)
    finally:lock.unlink(missing_ok=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime');p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:print('DRY_RUN_ONLY — no metered API, no endpoint probe')
    elif not a.runtime:p.error('--runtime required')
    else:run(a.runtime)
