"""Print local source excerpts, never a public clinical artifact."""
import argparse
import common095 as c
def main():
    p=argparse.ArgumentParser();p.add_argument('start',type=int);p.add_argument('--n',type=int,default=8);p.add_argument('--full',action='store_true');a=p.parse_args()
    rows=[r for r in c.lines(c.PRIVATE/'diagnosis_cases.jsonl') if r['review_owner']=='root']
    for i,r in enumerate(rows[a.start:a.start+a.n],a.start):
        print('\nCASE',i,r['id'],r['group'],'GT',r['GT'],'raw/G',r['B_raw'],r['B_G'],'CLAIM',r['claim'])
        if a.full:print(r['reference'])
        else:
            for e in r['relevant_entries']:print('ENTRY',e['reference_id'],e['text'])
if __name__=='__main__':main()
