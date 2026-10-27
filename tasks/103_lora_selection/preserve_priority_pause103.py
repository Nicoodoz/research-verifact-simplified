"""Preserve the entire interrupted stream; resume only unanswered IDs, without scoring."""
import json,hashlib,time
from pathlib import Path
r=Path('/root/autodl-tmp/verifact103/results');p=r/'qwen3.5-9b/eval/native_base.jsonl';out=r/'scheduling';out.mkdir(exist_ok=True)
before=(out/'native9b_before_priority_pause.jsonl').read_bytes();raw=p.read_bytes();assert raw.startswith(before)
lines=raw.splitlines(keepends=True);done=[];pending=[]
for line in lines:
 row=json.loads(line)
 if row['parsed'].get('finish_reason')=='stop':done.append(line)
 else:
  assert row['parsed'].get('finish_reason')=='budget_stop'
  pending.append(row)
assert pending and len(done)==len(before.splitlines()) and b''.join(done)==before
archive=out/'native9b_interrupted_stream.jsonl';assert not archive.exists();p.rename(archive);p.write_bytes(b''.join(done))
record=dict(epoch=time.time(),reason='User-directed reprioritization to3.6 resources; not budget exhaustion or a classification failure',completed_kept=len(done),incomplete_receipts_preserved=len(pending),pending_batch_ids=sorted({i for row in pending for i in row['batch_ids']}),archive_sha256=hashlib.sha256(raw).hexdigest(),completed_sha256=hashlib.sha256(before).hexdigest(),no_completed_answer_repeated=True,no_results_deleted=True,original_stream=str(archive))
(out/'priority_pause.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
