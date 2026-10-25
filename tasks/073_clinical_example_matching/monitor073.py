"""Read-only progress: no result-dependent decisions or reissues."""
import json,collections,statistics
from materials073 import OUT,read
import run073 as r
a,ans=r.attempt_state()
print(json.dumps(dict(attempts=len(a),http_status=dict(collections.Counter(str(x['http_status']) for x in a)),answered=len(ans),used_or_reserved_cny=sum(x['cost_cny'] for x in a),parse_status=dict(collections.Counter(x['parsed'].get('status') for x in ans.values()))),ensure_ascii=False))
