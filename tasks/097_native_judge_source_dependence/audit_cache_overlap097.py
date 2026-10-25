"""Post-run exact-cache correction; preserve all original calls and ledgers."""
import sqlite3
import common097 as c
from analyze_a import parse_arm

def main():
    hits=c.lines(c.OUT/'a_cache_selected_corrected_external.jsonl');assert len(hits)==4 and all(r['arm']=='published_B' for r in hits)
    rows={r['id']:r for r in c.lines(c.OUT/'a_same_id.jsonl')};jobs={(j['id'],j['arm']):j for j in c.lines(c.PRIVATE/'a_execution_jobs_corrected.jsonl')}
    con=sqlite3.connect(c.PRIVATE/'budget.sqlite');ledger={r[0]:r[1] for r in con.execute('SELECT rid,charge FROM attempts')};con.close()
    out=[]
    for hit in hits:
        tr=c.read(c.ROOT/hit['receipt_path'])['transport'];p,lab=parse_arm(tr,None)
        pid=hit['id'];j=jobs[pid,'published_B'];new=rows[pid]['predictions']['published_B']
        out.append(dict(id=pid,historical_receipt_sha256=hit['receipt_sha256'],current_receipt_sha256=rows[pid]['arms']['published_B']['receipt_sha256'],body_sha256=j['body_sha256'],old_raw=lab['raw'],new_raw=new,raw_changed=lab['raw']!=new,avoidable_new_busy_price_cny=ledger[j['request_id']]))
    c.write_lines(c.OUT/'a_cache_overlap_cases.jsonl',out)
    z=dict(exact_historical_hits=4,source='078_component_ablation published-reference V4 body',old_new_raw_changes=sum(r['raw_changed'] for r in out),avoidable_new_busy_price_cny=sum(r['avoidable_new_busy_price_cny'] for r in out),actual_097_paid_cost_unchanged=True,classification_results_unchanged=True,correction='Initial scan used pre-serialization-correction bodies. First post-run corrected scan failed to exclude local 097 paths due Windows separator mismatch, yielding 480 self-hits; final external-only scan found four historical 078 exact bodies. All 4 new HTTP200 are retained; no substitution or replay.')
    c.write_json(c.OUT/'a_cache_overlap_summary.json',z);print(z)
if __name__=='__main__':main()
