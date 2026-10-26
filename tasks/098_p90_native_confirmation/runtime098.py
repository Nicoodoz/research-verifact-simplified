"""Durable single-task ledger, bounded retries and exact successful-call reuse."""
import concurrent.futures as cf
import datetime as dt
import json
import os
import sqlite3
import sys
import time
import argparse
import common098 as c
sys.path.insert(0, str(c.ROOT / 'tasks/024_lambda2_transfer_validation'))
from transport_direct024 import DirectClient
from verifact_research.inference.aliyun import load_config

RETRY = {0, 408, 429, 500, 502, 503, 504}

def db():
    c.PRIVATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(c.PRIVATE / 'budget.sqlite', timeout=60)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS attempts(rid TEXT,num INTEGER,arm TEXT,charge REAL,status INTEGER,folder TEXT,PRIMARY KEY(rid,num))')
    return con

def accounting(j, tr, reservation):
    if not tr or tr.get('http_status') != 200 or tr.get('outcome_unknown'):
        return reservation, 'reserved_unknown_or_unsuccessful'
    try:
        response = json.loads(tr['body_text'])
        assert response['model'] == c.MODEL
        u = response['usage']
        i, o = u['prompt_tokens'], u['completion_tokens']
        cached = u.get('prompt_tokens_details', {}).get('cached_tokens', 0)
        assert all(type(x) is int and x >= 0 for x in [i, o, cached]) and cached <= i
        start, end = (dt.datetime.fromisoformat(tr[k]) for k in ['started_utc', 'ended_utc'])
        # Endpoint time origin is not exposed; crossing any peak/idle boundary is high priced.
        idle = c.is_idle(start) and c.is_idle(end) and (end-start).total_seconds() < 3600
        value = ((i-cached)*3 + cached*.3 + o*9)/1e6 * (.5 if idle else 1)
        assert value <= reservation + 1e-9
        return value, 'usage_idle' if idle else 'usage_peak_or_boundary'
    except (KeyError, ValueError, TypeError, AssertionError):
        return reservation, 'reserved_unverified_usage'

def summary():
    con = db()
    rows = con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts ORDER BY rowid').fetchall()
    con.close()
    return dict(attempts=len(rows), HTTP200=sum(r[4] == 200 for r in rows),
                used_or_reserved_cny=sum(r[3] for r in rows), hard_cap_cny=c.CAP,
                by_arm={a:dict(attempts=sum(r[2] == a for r in rows), HTTP200=sum(r[2] == a and r[4] == 200 for r in rows),
                               cost_or_reserved_cny=sum(r[3] for r in rows if r[2] == a)) for a in sorted({r[2] for r in rows})})

def completed():
    con = db()
    rows = con.execute('SELECT rid,folder FROM attempts WHERE status=200 ORDER BY rowid').fetchall()
    con.close()
    out = {}
    for rid, folder in rows:
        assert rid not in out, 'duplicate successful logical request'
        out[rid] = c.ROOT / folder
    return out

def reconcile():
    con = db()
    for p in (c.PRIVATE / 'attempts').glob('*/request.json'):
        req = c.read(p)
        receipt = p.parent / 'receipt.json'
        tr = c.read(receipt)['transport'] if receipt.exists() else None
        charge, _ = accounting(req['job'], tr, req['reservation_cny'])
        con.execute('INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?)',
                    (req['job']['request_id'], req['attempt'], req['job']['arm'], charge,
                     tr['http_status'] if tr else 0, p.parent.relative_to(c.ROOT).as_posix()))
    con.commit()
    con.close()

def process(j, operating=48.0):
    cfg = load_config(c.ROOT / '.env.aliyun')
    assert cfg.base_url.rstrip('/') == c.ENDPOINT and cfg.model == c.MODEL
    client = DirectClient(cfg, timeout=240)
    for _ in range(3):
        con = db()
        con.execute('BEGIN IMMEDIATE')
        old = con.execute('SELECT num,status FROM attempts WHERE rid=? ORDER BY num', (j['request_id'],)).fetchall()
        if any(status == 200 for _, status in old):
            con.rollback(); con.close(); return 'cached'
        n = max([x[0] for x in old], default=0) + 1
        if n > 3:
            con.rollback(); con.close(); return 'retry_exhausted'
        # Busy reservation even in idle: protects a hung call across tariff boundary.
        reservation = j['busy_bound_cny']
        used = con.execute('SELECT COALESCE(SUM(charge),0) FROM attempts').fetchone()[0]
        if used + reservation > min(operating, c.CAP):
            con.rollback(); con.close(); return 'budget_stop'
        folder = c.PRIVATE / 'attempts' / f"{j['request_id']}_{n}"
        folder.mkdir(parents=True, exist_ok=False)
        c.put(folder / 'request.json', dict(job=j, attempt=n, utc=c.utc(), prior_used_or_reserved_cny=used,
              reservation_cny=reservation, hard_cap_cny=c.CAP, operating_cap_cny=operating,
              endpoint=cfg.base_url))
        con.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)', (j['request_id'], n, j['arm'], reservation, 0, folder.relative_to(c.ROOT).as_posix()))
        con.commit(); con.close()
        t0 = time.monotonic()
        try:
            tr = client.send(j['body'])
        except Exception as e:
            tr = dict(http_status=0, body_text='', outcome_unknown=True, error_type=type(e).__name__, started_utc=c.utc(), ended_utc=c.utc())
        tr['elapsed_seconds'] = time.monotonic() - t0
        c.put(folder / 'receipt.json', dict(request_sha256=c.sha(folder / 'request.json'), transport=tr))
        charge, basis = accounting(j, tr, reservation)
        c.put(folder / 'accounting.json', dict(cost_or_reserved_cny=charge, basis=basis, reservation_cny=reservation))
        con = db()
        con.execute('UPDATE attempts SET charge=?,status=? WHERE rid=? AND num=?', (charge, tr['http_status'], j['request_id'], n))
        con.commit(); con.close()
        if tr['http_status'] == 200:
            response = json.loads(tr['body_text'])
            if response.get('model') != c.MODEL:
                raise RuntimeError('returned_model_mismatch')
            if basis == 'reserved_unverified_usage':
                raise RuntimeError('successful_usage_not_verifiable')
            return 'success'
        if tr['http_status'] not in RETRY:
            raise RuntimeError('nonretryable_HTTP_' + str(tr['http_status']))
        if n < 3:
            time.sleep(3 * 2**(n-1))
    return 'retry_exhausted'

def run(jobs, workers=4):
    reconcile()
    succeeded = completed()
    todo = [j for j in jobs if j['request_id'] not in succeeded]
    active = {}; index = 0; stopped = False; last = time.monotonic()
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        try:
            while (index < len(todo) and not stopped) or active:
                while index < len(todo) and not stopped and len(active) < workers:
                    j = todo[index]; index += 1
                    active[pool.submit(process, j)] = j
                if not active:
                    break
                ready, _ = cf.wait(active, timeout=2, return_when=cf.FIRST_COMPLETED)
                for fut in ready:
                    j = active.pop(fut)
                    result = fut.result()
                    if result in {'budget_stop', 'retry_exhausted'}:
                        stopped = True
                        print(result, j['request_id'], flush=True)
                if time.monotonic()-last >= 30:
                    print(c.canonical(dict(progress=summary(), queued=len(todo)-index, active=len(active))), flush=True)
                    last = time.monotonic()
        except BaseException:
            # Running calls settle and persist before the exception escapes.
            for f in active:
                f.cancel()
            raise
    print(c.canonical(dict(finished=True, requested=len(jobs), succeeded=sum(j['request_id'] in completed() for j in jobs), ledger=summary())), flush=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['aux', 'busy', 'remaining', 'status'])
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.mode == 'status':
        print(c.canonical(summary())); return
    freeze = c.read(c.OUT / ('aux_freeze.json' if args.mode == 'aux' else 'execution_freeze.json'))
    for rel, checksum in freeze['files'].items():
        assert c.sha(c.ROOT / rel) == checksum, rel
    jobs = c.lines(c.PRIVATE / ('aux_jobs.jsonl' if args.mode == 'aux' else 'jobs.jsonl'))
    if args.mode == 'busy':
        jobs = [j for j in jobs if j['request_id'] in freeze['busy_first_request_ids']]
    if args.mode == 'remaining' and not c.is_idle():
        raise RuntimeError('Remaining frozen panel is scheduled for idle tariff; no busy auto-expansion')
    lock = c.PRIVATE / 'run.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    try:
        run(jobs, args.workers)
    finally:
        lock.unlink()

if __name__ == '__main__':
    main()
