import statistics
from collections import Counter
import common103 as c
def stats(vals):
 vals=sorted(vals)
 return dict(N=len(vals),sum=sum(vals),mean=statistics.mean(vals),p50=vals[int(.5*(len(vals)-1))],p90=vals[int(.9*(len(vals)-1))],p95=vals[int(.95*(len(vals)-1))],p99=vals[int(.99*(len(vals)-1))],max=max(vals),over16k=sum(x>16384 for x in vals),over32k=sum(x>32768 for x in vals))
def main():
 lengths=c.lines(c.OUT/'token_lengths.jsonl');sample=c.lines(c.PRIVATE/'sample240.jsonl');local={r['id'] for r in sample if r['local180']};train=c.lines(c.PRIVATE/'train512.jsonl');first={r['id'] for r in train[:256]};out={}
 for m in c.REPOS:
  rr=[r for r in lengths if r['model']==m]
  out[m]={key:stats([r[mode] for r in rr if test(r)]) for key,mode,test in [('all_training','label',lambda r:r['role']=='train'),('train512','label',lambda r:r['train512']),('train256','label',lambda r:r['id'] in first),('api240','native',lambda r:r['api240']),('local180','native',lambda r:r['id'] in local)]}
 c.put(c.OUT/'length_summary.json',out);print(c.canonical(out['qwen3.5-9b']))
if __name__=='__main__':main()
