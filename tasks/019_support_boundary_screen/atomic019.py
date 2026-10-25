"""019-only atomic writes resilient to brief Windows file-sharing conflicts."""
import json
import os
from pathlib import Path
import tempfile
import time


def save(path, value, *, new=False):
    path = Path(path)
    if new and path.exists():
        raise ValueError('Refusing to overwrite an existing artifact')
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True,
                         separators=(',', ':'), allow_nan=False) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
            dir=path.parent, prefix='.pending-', suffix='.json', delete=False) as f:
        temporary = Path(f.name)
        f.write(encoded)
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(12):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == 11:
                raise
            time.sleep(min(0.05 * 2 ** attempt, 1.0))
