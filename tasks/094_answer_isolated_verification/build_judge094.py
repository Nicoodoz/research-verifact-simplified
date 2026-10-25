import common094 as c
import method094 as m
from prepare094 import job
def main():
    rows=c.lines(c.PRIVATE/'inputs.jsonl');qs={r['id']:r for r in c.lines(c.PRIVATE/'questions_reviewed.jsonl')};records={(r['id'],r['arm']):r for r in c.lines(c.PRIVATE/'extracted_aligned.jsonl')};t=c.read(c.PRIVATE/'judge_template.json');alloc=c.read(c.OUT/'design_freeze.json')['allocations'];jobs=[];aliases=[]
    for r in rows:
        seen={}
        for arm in ['B','V','Q']:
            b=m.judge_body(t,r) if arm=='B' or r['id'] not in qs else m.judge_body(t,r,qs[r['id']],records[r['id'],arm]['record'])
            j=job(r['id'],'judge',arm,b);assert j['bound_cny']<=alloc[r['id']]['judge_'+arm]
            if j['body_sha256'] in seen:j=seen[j['body_sha256']]
            else:seen[j['body_sha256']]=j;jobs.append(j)
            aliases.append(dict(id=r['id'],arm=arm,request_id=j['request_id'],body_sha256=j['body_sha256'],operated=r['id'] in qs))
    c.putl(c.PRIVATE/'judge_jobs.jsonl',jobs);c.putl(c.OUT/'judge_aliases.jsonl',aliases)
    sources=[c.PRIVATE/'judge_jobs.jsonl',c.OUT/'judge_aliases.jsonl',c.OUT/'question_review.json',c.PRIVATE/'questions_reviewed.jsonl',c.PRIVATE/'extracted_aligned.jsonl',c.TASK/'grounding094.py',c.TASK/'align_sources094.py',c.TASK/'build_judge094.py',c.TASK/'extraction094.py',c.TASK/'review_questions094.py',c.TASK/'build_extract094.py']
    c.put(c.OUT/'judge_freeze.json',dict(utc=c.now(),requests=len(jobs),positions=len(aliases),sources={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in sources},primary='Q-B and Q-V PriorG; raw secondary; no posthoc rule choice',invalid='No historical imputation; common core and own common raw, full-N coverage',no_final_results_seen=True))
    print('Frozen final jobs',len(jobs),'logical',len(aliases))
if __name__=='__main__':main()
