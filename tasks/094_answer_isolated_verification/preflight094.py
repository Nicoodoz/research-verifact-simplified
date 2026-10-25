import common094 as c
import api094,method094 as m
def main():
    _,s=api094.state();out=[]
    for j in c.lines(c.PRIVATE/'preflight_jobs.jsonl'):
        import json
        tr=s[j['request_id']]['tr'];p=m.parse_qa(tr,json.loads(j['body']['messages'][1]['content'])['reference'])
        assert p['valid'],p
        out.append(dict(arm=j['arm'],valid=p['valid'],record=p['record'],citations=p['citations']))
    c.put(c.OUT/'preflight_result.json',dict(status='PASS',synthetic_only=True,results=out,utc=c.now()))
    print('Synthetic source binding preflight PASS')
if __name__=='__main__':main()
