"""Fixed 12-case temporal sensitivity for identical B input/body."""
import sqlite3
from collections import Counter
import common097 as c
from analyze_a import parse_arm

def main():
    jobs=c.lines(c.PRIVATE/'a_bridge_jobs.jsonl');old={r['id']:r for r in c.lines(c.ROOT/'outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl')}
    con=sqlite3.connect(c.PRIVATE/'budget.sqlite')
    done={r[0]:(r[1],r[2],r[3]) for r in con.execute("SELECT rid,status,folder,charge FROM attempts WHERE arm='C48_B_bridge'")};con.close()
    rows=[]
    for j in jobs:
        if j['request_id'] not in done:continue
        status,folder,charge=done[j['request_id']]
        if status!=200:continue
        tr=c.read(c.ROOT/folder/'receipt.json')['transport'];p,labels=parse_arm(tr,None);o=old[j['id']]
        old_req=c.read(c.ROOT/o['B']['request_path']);old_body=old_req['job']['body'] if 'job' in old_req else old_req['body']
        assert c.digest(c.canonical(old_body))==j['body_sha256']
        rows.append(dict(id=j['id'],sid=o['sid'],GT=o['GT'],old_raw=o['predictions']['B_raw'],new_raw=labels['raw'],old_PriorG=o['predictions']['B_PriorG'],new_PriorG=labels['PriorG'] if p['valid'] else None,raw_valid=p['raw_valid'],score_valid=p['scores_valid'],core_valid=p['valid'],same_body=True,new_receipt_sha256=c.sha(c.ROOT/folder/'receipt.json'),cost_busy_cny=charge))
    c.write_lines(c.OUT/'a_bridge_same_id.jsonl',rows)
    z=dict(frozen_N=len(jobs),HTTP200=len(rows),patients=len({r['sid'] for r in rows}),raw_valid=sum(r['raw_valid'] for r in rows),core_valid=sum(r['core_valid'] for r in rows),raw_label_changes=sum(r['old_raw']!=r['new_raw'] for r in rows),final_label_changes=sum(r['new_PriorG'] is not None and r['old_PriorG']!=r['new_PriorG'] for r in rows),old_raw_correct=sum(r['old_raw']==r['GT'] for r in rows),new_raw_correct=sum(r['new_raw']==r['GT'] for r in rows),cost_busy_cny=sum(r['cost_busy_cny'] for r in rows),interpretation='Pre-selected temporal sensitivity only; 12 is too small to explain all A changes or establish stability of any rescue.')
    c.write_json(c.OUT/'a_bridge_summary.json',z);print(z)
if __name__=='__main__':main()
