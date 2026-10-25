"""Exact-body, exact-backend success inventory for three new A arms."""
import json, subprocess,sys
from collections import Counter
import common097 as c

def body(req):
    if isinstance(req.get('job'),dict) and isinstance(req['job'].get('body'),dict):return req['job']['body']
    for k in ('body','request_body'):
        if isinstance(req.get(k),dict):return req[k]
    return None

def main(corrected=False):
    jobs=c.lines(c.PRIVATE/('a_execution_jobs_corrected.jsonl' if corrected else 'a_jobs.jsonl'));wanted={j['body_sha256']:j for j in jobs};hits={};counter=Counter()
    paths=subprocess.check_output(['rg','--files','-uu','outputs','.local_models','-g','request.json','-g','!**/venv/**','-g','!**/site-packages/**'],cwd=c.ROOT,text=True,encoding='utf-8').splitlines()
    for path in paths:
        if path.replace('\\','/').startswith('.local_models/097_native_judge_source_dependence/'):continue
        try:
            p=c.ROOT/path; b=body(c.read(p))
            if not b:continue
            h=c.digest(c.canonical(b))
            if h not in wanted:continue
            rp=p.parent/'receipt.json'
            if not rp.exists():continue
            tr=c.read(rp);tr=tr.get('transport',tr)
            if tr.get('http_status')!=200:continue
            native=json.loads(tr['body_text'])
            if native.get('model')!=c.MODEL:continue
            counter[wanted[h]['arm']]+=1
            old=hits.get(h)
            new=dict(id=wanted[h]['id'],arm=wanted[h]['arm'],body_sha256=h,request_path=path,receipt_path=rp.relative_to(c.ROOT).as_posix(),receipt_sha256=c.sha(rp))
            if old is None or new['request_path']<old['request_path']:hits[h]=new
        except (KeyError,ValueError,TypeError,AssertionError):continue
    suffix='_corrected_external' if corrected else ''
    c.write_lines(c.OUT/f'a_cache_selected{suffix}.jsonl',sorted(hits.values(),key=lambda x:(x['id'],x['arm'])))
    stats=dict(scanned_request_files=len(paths),compatible_success_candidates=dict(counter),unique_exact_body_cached=len(hits),missing_by_arm=dict(Counter(j['arm'] for j in jobs if j['body_sha256'] not in hits)),selection='lexically first path among HTTP200 exact-body/returned-model matches; no outcome selection')
    c.write_json(c.OUT/f'a_cache_inventory{suffix}.json',stats)
    print(stats)
if __name__=='__main__':main('--corrected' in sys.argv)
