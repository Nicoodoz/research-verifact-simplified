"""Lightweight receipt-only progress; no clinical parsing or GT joins."""
import datetime,json,collections
import common096 as c
import marlin096 as m
def main():
    rows=[];pending=0
    for f in (m.P/'attempts').glob('*/*/request.json'):
        q=c.read(f);rp=f.parent/'receipt.json'
        if not rp.exists():pending+=1;continue
        r=c.read(rp);rows.append(dict(stage=q['stage'],http=r['http_status'],start=r['started_utc'],end=r['ended_utc']))
    counts=collections.Counter(r['stage'] for r in rows if r['http']==200);natural=counts['natural']+sum(counts[x] for x in ['P0','M1','M2','M3','M4']);done=counts['calibration']+natural+counts['diagnostic']
    now=datetime.datetime.now(datetime.timezone.utc);rates={}
    for stage in ['calibration','natural','diagnostic']:
        rr=[x for x in rows if x['stage']==stage and x['http']==200]
        if rr:
            first=min(datetime.datetime.fromisoformat(x['start']) for x in rr);last=max(datetime.datetime.fromisoformat(x['end']) for x in rr)
            duration=((last if counts[stage]>=dict(calibration=143,natural=759,diagnostic=200)[stage] else now)-first).total_seconds()
            rates[stage]=round(len(rr)/duration*60,3)
    out=dict(utc=c.now(),HTTP200=done,total=1143,calibration=counts['calibration'],natural=natural,diagnostic=counts['diagnostic'],remaining=1143-done,incomplete_attempts=pending,http_statuses=dict(collections.Counter(str(x['http']) for x in rows)),new_request_rates_per_min=rates,GT_read=False)
    c.append(m.O/'progress_corrected.jsonl',out)
    print(json.dumps(out),flush=True)
if __name__=='__main__':main()
