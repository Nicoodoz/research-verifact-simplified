"""098 immutable artifacts and shared pure utilities; no implicit model calls."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/098_p90_native_confirmation'
PRIVATE = ROOT / '.local_models/098_p90_native_confirmation'
MODEL = 'deepseek-v4-flash-0731'
ENDPOINT = 'https://maas.qianwenaiapi.com/compatible-mode/v1'
CAP = 50.0
LABELS = ('Supported', 'Not Supported', 'Not Addressed')
sys.path.insert(0, str(ROOT / 'src'))

def canonical(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(x):
    return hashlib.sha256(x.encode('utf-8')).hexdigest()

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def lines(p):
    with Path(p).open(encoding='utf-8-sig') as f:
        return [json.loads(s) for s in f if s.strip()]

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def put(p, x):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if p.exists():
        assert p.read_bytes() == data, f'Immutable artifact differs: {p}'
        return
    with p.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

def putl(p, rows):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = ''.join(canonical(r) + '\n' for r in rows).encode('utf-8')
    if p.exists():
        assert p.read_bytes() == data, f'Immutable artifact differs: {p}'
    else:
        with p.open('xb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())

def atomic(p, x):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + '.tmp')
    tmp.write_bytes((json.dumps(x, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8'))
    tmp.replace(p)

def is_idle(when=None):
    when = when or dt.datetime.now(dt.timezone.utc)
    hour = when.astimezone(dt.timezone(dt.timedelta(hours=8))).hour
    return hour >= 22 or hour < 8

def bound(body, idle=False):
    # UTF-8 byte count dominates BPE input tokens; 2048 covers message framing.
    n = len(canonical(body).encode('utf-8')) + 2048
    return (n * 3 + body['max_tokens'] * 9) / 1e6 * (0.5 if idle else 1)

def job(body, arm, pid, panel, repeat=0):
    rid = digest(canonical(['098/v1', arm, pid, panel, repeat, digest(canonical(body))]))[:28]
    return dict(request_id=rid, arm=arm, id=pid, panel=panel, repeat=repeat,
                body=body, body_sha256=digest(canonical(body)), busy_bound_cny=bound(body))

def parse_native(tr):
    try:
        response = json.loads(tr['body_text'])
        assert tr['http_status'] == 200 and response['model'] == MODEL
        choice = response['choices'][0]
        def unique(pairs):
            obj = {}
            for k, v in pairs:
                if k in obj:
                    raise ValueError('duplicate JSON key')
                obj[k] = v
            return obj
        obj = json.loads(choice['message']['content'], object_pairs_hook=unique)
        assert isinstance(obj, dict) and obj.get('verdict') in LABELS
        reason_ok = isinstance(obj.get('reason'), str) and bool(obj['reason'].strip())
        return dict(verdict=obj['verdict'], valid=True, reason_present=reason_ok,
                    finish_reason=choice.get('finish_reason'),
                    format_anomaly=not reason_ok or choice.get('finish_reason') != 'stop')
    except (AssertionError, ValueError, KeyError, TypeError, IndexError):
        return dict(verdict=None, valid=False, reason_present=False, format_anomaly=True)
