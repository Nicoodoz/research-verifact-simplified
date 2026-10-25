"""Add native arm to the already frozen 12-case concurrent sensitivity; keep v1."""
import common097 as c

def main():
    bridge=c.lines(c.OUT/'a_bridge_same_id.jsonl');a={r['id']:r for r in c.lines(c.OUT/'a_same_id.jsonl')}
    rows=[]
    for r in bridge:
        n=a[r['id']]['predictions']['C48_native'];g=r['GT'];b=r['new_raw'];o=r['old_raw']
        rows.append(dict(id=r['id'],sid=r['sid'],GT=g,old_B_raw=o,current_B_raw=b,current_native_raw=n,old_B_correct=o==g,current_B_correct=b==g,current_native_correct=n==g,current_native_vs_current_B='rescue' if b!=g and n==g else 'harm' if b==g and n!=g else 'same_correct' if b==n==g else 'other'))
    c.write_lines(c.OUT/'a_bridge_contemporaneous.jsonl',rows)
    z=dict(N=len(rows),patients=len({r['sid'] for r in rows}),old_B_correct=sum(r['old_B_correct'] for r in rows),current_B_correct=sum(r['current_B_correct'] for r in rows),current_native_correct=sum(r['current_native_correct'] for r in rows),native_rescue_vs_current_B=sum(r['current_native_vs_current_B']=='rescue' for r in rows),native_harm_vs_current_B=sum(r['current_native_vs_current_B']=='harm' for r in rows),note='Small preselected temporal bridge; descriptive only, not the 160-case primary comparison or stability proof.')
    c.write_json(c.OUT/'a_bridge_contemporaneous_summary.json',z);print(z)
if __name__=='__main__':main()
