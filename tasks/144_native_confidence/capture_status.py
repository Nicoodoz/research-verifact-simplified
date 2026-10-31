"""Read only engineering progress; omit generated content and classification metrics."""
from pathlib import Path
import argparse
import json
import os
import time


def read(path):
    try:return json.loads(path.read_text())
    except (FileNotFoundError,json.JSONDecodeError):return None


def status(stage):
    stage=Path(stage);job=read(stage/'bundle/data/job.json');out=stage/'results'
    records=[]
    for call in job['calls']:
        row=read(out/call['variant']/call['mode']/(call['id']+'.json'))
        if row is not None:records.append(row)
    pid=read(stage/'pid.json');alive=False
    if pid:
        try:os.kill(pid['pid'],0);alive=True
        except ProcessLookupError:pass
    done=read(stage/'controller_done.json')
    return dict(task='144_capture_pilot',epoch=time.time(),expected_calls=24,completed_calls=len(records),
        by_mode={mode:sum(r['mode']==mode for r in records) for mode in ('control','capture')},
        complete_pairs=sum(all(any(r['variant']==v and r['id']==i and r['mode']==m for r in records)
            for m in ('control','capture')) for v,i in {(c['variant'],c['id']) for c in job['calls']}),
        valid_first_answers=sum(bool(r['parsed']['valid']) for r in records),
        captured_prefixes=sum(r['mode']=='capture' and r['capture']['status']=='captured' for r in records),
        generation_seconds=sum(r['generation_seconds'] for r in records),
        pid=pid,controller_alive=alive,controller_done=done,runtime=read(out/'runtime.json'),
        complete=read(out/'complete.json'),run_exit=read(out/'run_exit.json'),inflight=read(out/'inflight.json'),
        terminal=bool(done) or bool(pid and not alive),engineering_only=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(status(args.stage)))


if __name__=='__main__':main()
