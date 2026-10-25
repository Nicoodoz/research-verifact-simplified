"""Read-only access to successful native receipts and public attempt accounting."""
import sqlite3,json
import common095 as c

def success_index():
    con=sqlite3.connect('file:'+str(c.PRIVATE/'budget.sqlite')+'?mode=ro',uri=True)
    rows=con.execute('SELECT rid,num,folder FROM attempts WHERE status=200 ORDER BY rid,num').fetchall();con.close();out={}
    for rid,num,folder in rows:out.setdefault(rid,dict(folder=folder,attempt=num))
    return out

def receipt(info):return c.read(c.ROOT/info['folder']/'receipt.json')['transport']

def successful_jobs():
    out={}
    for rid,s in success_index().items():
        req=c.read(c.ROOT/s['folder']/'request.json');out[rid]=dict(s,job=req['job'],utc=req['utc'])
    return out

def attempts():
    con=sqlite3.connect('file:'+str(c.PRIVATE/'budget.sqlite')+'?mode=ro',uri=True)
    rows=con.execute('SELECT rid,num,phase,reserved,charge,status,folder FROM attempts ORDER BY rowid').fetchall();con.close();out=[]
    for rid,num,phase,bound,charge,status,folder in rows:
        fp=c.ROOT/folder;req=c.read(fp/'request.json');rp=fp/'receipt.json';j=req['job'];tr=c.read(rp)['transport'] if rp.exists() else None
        usage=None
        if tr:
            try:usage=json.loads(tr['body_text']).get('usage')
            except (ValueError,TypeError):pass
        out.append(dict(request_id=rid,attempt=num,id=j['id'],arm=j['arm'],phase=phase,reserved_cny=bound,charge_or_reserved_cny=charge,http_status=status,utc=req['utc'],body_sha256=j['body_sha256'],request_path=(fp/'request.json').relative_to(c.ROOT).as_posix(),request_sha256=c.sha(fp/'request.json'),receipt_path=rp.relative_to(c.ROOT).as_posix() if rp.exists() else None,receipt_sha256=c.sha(rp) if rp.exists() else None,usage=usage,elapsed_seconds=tr.get('client_elapsed_seconds') if tr else None,prior_task_reserved=req['prior_task_reserved'],prior_phase_reserved=req['prior_phase_reserved']))
    return out
