"""Check task artifacts against local API secrets without printing their values."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
secrets = []
for env in (ROOT / '.env.aliyun', ROOT / '.env.siliconflow_pool'):
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                value = value.strip().strip('\"\'')
                if ('KEY' in key.upper() or 'TOKEN' in key.upper()) and len(value) >= 16:
                    secrets.append(value.encode())
assert secrets, 'No local secrets available for this check'
checked = 0
for folder in ('tasks/036_final_validation', 'outputs/036_final_validation'):
    for path in (ROOT / folder).rglob('*'):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        checked += 1
        with path.open('rb') as stream:
            tail = b''
            while block := stream.read(1024 * 1024):
                data = tail + block
                assert not any(secret in data for secret in secrets), str(path.relative_to(ROOT))
                tail = data[-max(map(len, secrets)):]
print(json.dumps({'status': 'PASS', 'files_checked': checked, 'secret_values_printed': False}))
