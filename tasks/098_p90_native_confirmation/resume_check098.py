"""Offline pre-resume verification; never sends requests or reads target quality."""
import sqlite3
import common098 as c

def main():
    freeze=c.read(c.OUT/'execution_freeze.json')
    for rel,checksum in freeze['files'].items():
        assert c.sha(c.ROOT/rel)==checksum,rel
    jobs=c.lines(c.PRIVATE/'jobs.jsonl')
    assert len(jobs)==freeze['jobs'] and len({j['request_id'] for j in jobs})==len(jobs)
    con=sqlite3.connect(f'file:{(c.PRIVATE/"budget.sqlite").as_posix()}?mode=ro',uri=True)
    attempts=con.execute('SELECT rid,num,arm,charge,status,folder FROM attempts').fetchall();con.close()
    success=[r[0] for r in attempts if r[4]==200]
    assert len(success)==len(set(success)), 'duplicate successful logical request'
    assert set(freeze['busy_first_request_ids'])<=set(success)
    for rid,number,arm,charge,status,folder in attempts:
        req=c.read(c.ROOT/folder/'request.json')
        if status==200:
            rp=c.ROOT/folder/'receipt.json';receipt=c.read(rp)
            assert receipt['request_sha256']==c.sha(c.ROOT/folder/'request.json')
            assert receipt['transport']['http_status']==200
        assert req['job']['request_id']==rid and req['attempt']==number
        assert req['prior_used_or_reserved_cny']+req['reservation_cny']<=req['operating_cap_cny']<=50
    used=sum(r[3] for r in attempts)
    assert used<=50
    print(c.canonical(dict(status='READY',utc=c.utc(),frozen_files_verified=len(freeze['files']),
          target_requests=len(jobs),successful_target_requests=sum(j['request_id'] in success for j in jobs),
          remaining_target_requests=sum(j['request_id'] not in success for j in jobs),
          attempts=len(attempts),HTTP200=len(success),used_or_reserved_cny=used,
          first32_preserved=True,no_network_or_new_requests=True)))

if __name__=='__main__':main()
