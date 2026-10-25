"""Pre-send correction: B payload must match the exact compact historical serialization."""
import json
import common097 as c

def main():
    old=c.lines(c.PRIVATE/'a_execution_jobs.jsonl');corrected=[]
    for j in old:
        j=json.loads(c.canonical(j))
        if j['arm']=='published_B':
            payload=json.loads(j['body']['messages'][1]['content'])
            j['body']['messages'][1]['content']=json.dumps(payload,ensure_ascii=False,separators=(',',':'))
            j['body_sha256']=c.digest(c.canonical(j['body']))
            j['bound_cny']=((len(c.canonical(j['body']).encode('utf-8'))+2000)*3+8192*9)/1e6
        corrected.append(j)
    c.write_lines(c.PRIVATE/'a_execution_jobs_corrected.jsonl',corrected)
    c.write_json(c.OUT/'a_request_correction.json',dict(utc=c.utc(),before_sha256=c.sha(c.PRIVATE/'a_execution_jobs.jsonl'),after_sha256=c.sha(c.PRIVATE/'a_execution_jobs_corrected.jsonl'),reason='Before any 097 paid call, comparison with cached B request showed compact JSON separators. Correct published_B user payload to exact current B serialization; no prompt, model, sample or outcome change.',affected_jobs=sum(j['arm']=='published_B' for j in corrected)))
    print('corrected published B jobs',sum(j['arm']=='published_B' for j in corrected))
if __name__=='__main__':main()
