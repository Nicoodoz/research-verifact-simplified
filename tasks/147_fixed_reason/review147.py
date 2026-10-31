"""Judge explanatory stance without seeing the frozen verdict or physician GT."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,json,sys,hashlib,time
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(Path(__file__).resolve().parent))
from api_budget147 import send
PROMPT='''Assess the semantic stance of each explanation toward its assertion. You are not checking medical truth. Infer the stance from the substantive explanation body, not by matching verdict words or accepting an appended verdict. Do not assume an explicit label is correct if the preceding explanation points in the opposite direction.
Use exactly one stance: Supported (assertion fully supported); Not Supported (assertion addressed but contradicted or only partially supported); Not Addressed (the specific assertion is not addressed by the supplied information); Ambiguous (direction unclear, internally conflicting, or insufficient substantive explanation). A related fact alone is not full support. Distinguish evidence of contradiction/partial support from a lack of addressing the assertion. Flag label_only=true when the explanation merely repeats a verdict without a substantive factual correspondence or limitation.
Return only JSON {"items":[{"key":"...","stance":"Supported|Not Supported|Not Addressed|Ambiguous","label_only":false,"brief_basis":"at most 20 words about the explanation body"}]}. Assess all supplied items. No expected verdicts or physician labels are provided.'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--arm',nargs='+',default=['reason120','reason_base9b'])
    ap.add_argument('--private-root',type=Path,default=R/'.local_models/147_fixed_reason');ap.add_argument('--api-task',default='147_fixed_reason')
    ap.add_argument('--max-tokens',type=int,default=2048);ap.add_argument('--workers',type=int,default=3);args=ap.parse_args()
    P=args.private_root.resolve()
    if not P.is_relative_to((R/'.local_models').resolve()):raise ValueError('Private task root required')
    data={r['id']:r for r in map(json.loads,(P/'inputs.jsonl').read_text(encoding='utf-8').splitlines())}
    cases=[]
    for arm in args.arm:
        for file in sorted((P/'evidence/results'/arm).glob('*.json')):
            row=json.loads(file.read_text());parsed=row.get('parsed') or {}
            if row.get('finish_reason')!='stop' or parsed.get('status')!='explained':continue
            key=hashlib.sha256((arm+'|'+row['id']).encode()).hexdigest()[:20]
            cases.append(dict(key=key,assertion=data[row['id']]['claim'],explanation=parsed['reason']))
    # The request contains neither fixed_verdict, GT, patient role, nor model identity.
    batches=[cases[i:i+4] for i in range(0,len(cases),4)];out=P/'semantic_review';out.mkdir(parents=True,exist_ok=True)
    def one(batch):
        identity=hashlib.sha256(json.dumps(batch,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]
        done=out/(identity+'.json')
        if done.exists():return json.loads(done.read_text())
        trials=[];valid=None
        for attempt in range(2):
            folder=out/(identity+f'_attempt{attempt}')
            if folder.exists():raise RuntimeError('Inspect earlier incomplete review attempt; do not silently resend')
            native,transport,elapsed=send([dict(role='system',content=PROMPT),dict(role='user',content=json.dumps({'items':batch},ensure_ascii=False))],folder,max_tokens=args.max_tokens,task=args.api_task)
            trials.append(dict(http_status=transport['http_status'],seconds=elapsed,usage=native.get('usage')))
            if transport['http_status']==200:
                try:
                    value=json.loads(native['choices'][0]['message']['content'])
                    items=value['items'];lookup={r['key']:r for r in items}
                    if len(lookup)!=len(batch) or set(lookup)!={r['key'] for r in batch}:raise ValueError('Wrong item coverage')
                    if any(r.get('stance') not in ('Supported','Not Supported','Not Addressed','Ambiguous') or type(r.get('label_only')) is not bool for r in items):raise ValueError('Invalid semantic fields')
                    valid=lookup
                except (ValueError,TypeError,KeyError,IndexError):pass
                break
            if transport['http_status'] not in (0,429,500,502,503,504):break
            if attempt==0:time.sleep(3)
        result=dict(batch=identity,expected_keys=[r['key'] for r in batch],valid=valid is not None,judgments=valid,trials=trials)
        done.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');return result
    results=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in as_completed([pool.submit(one,batch) for batch in batches]):results.append(future.result())
    summary=dict(reason_cases=len(cases),batches=len(results),valid_batches=sum(r['valid'] for r in results),
                 generated_review_epoch=time.time(),GT_or_fixed_label_in_review_input=False)
    (out/('summary_'+'_'.join(args.arm)+'.json')).write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary))

if __name__=='__main__':main()
