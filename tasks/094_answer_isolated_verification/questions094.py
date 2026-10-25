"""Build GT-blind question review file; no classification results consulted."""
import common094 as c
import api094,method094 as m
def main():
    _,s=api094.state();inputs={r['id']:r for r in c.lines(c.PRIVATE/'inputs.jsonl')};questions=[]
    for j in c.lines(c.PRIVATE/'generate_jobs.jsonl'):
        r=inputs[j['id']];q=m.parse_question(s[j['request_id']]['tr'],r['text']);questions.append(dict(id=r['id'],**q))
        print(r['id'],'CLAIM:',r['text'],'QUESTION:',q,flush=True)
    c.putl(c.PRIVATE/'questions.jsonl',questions)
if __name__=='__main__':main()
