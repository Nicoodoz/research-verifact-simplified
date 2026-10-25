"""GT-free local inspection of changed extraction records, no final verdicts."""
import common094 as c
def main():
    inputs={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};r={(x['id'],x['arm']):x for x in c.lines(c.PRIVATE/'extracted_aligned.jsonl')}
    for pid in inputs:
        if (pid,'V') not in r:continue
        v,q=r[pid,'V'],r[pid,'Q']
        if v['record']==q['record']:continue
        print('ID',pid,'CLAIM',inputs[pid]['text'])
        for arm,z in [('V',v),('Q',q)]:print(arm,z['record'])
if __name__=='__main__':main()
