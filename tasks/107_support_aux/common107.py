"""107 helpers: imports perform no network, model or GPU operations."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import uuid

ROOT = Path(__file__).resolve().parents[2]
TASK = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/107_support_aux'
PRIVATE = ROOT / '.local_models/107_support_aux'
LABELS = ('Supported', 'Not Supported', 'Not Addressed')
ARMS = ('label_only', 'support_aux')
REVISION = 'c202236235762e1c871ad0ccb60c8ee5ba337b9a'

def canonical(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig').splitlines() if line.strip()]

def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()

def utc():
    return datetime.now(timezone.utc).isoformat()

def put(path, value):
    _write(path, (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))

def putl(path, values):
    _write(path, ''.join(canonical(row) + '\n' for row in values).encode('utf-8'))

def write(path, text):
    _write(path, (text.rstrip() + '\n').encode('utf-8'))

def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)

def frozen(path, data):
    path = Path(path)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Existing frozen data differs: ' + str(path))
    if not path.exists():
        _write(path, data)
