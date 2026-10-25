"""Preserve historical navigation bytes and validate delivery manifests."""
import subprocess
import common036 as c

NAV = ['README.md', 'AGENTS.md', 'docs/PROJECT_STATUS.md',
       'docs/REPRODUCIBILITY.md', 'docs/RUN_ENVIRONMENT.md',
       'docs/API_POLICY.md', 'reviews/README.md']
for name in NAV:
    path = c.ROOT / name
    original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=c.ROOT)
    current = path.read_bytes()
    paragraph = current.decode('utf-8-sig').splitlines()[2]
    assert '036' in paragraph
    lines = original.splitlines(keepends=True)
    assert len(lines) > 2 and not lines[1].strip()
    ending = b'\r\n' if lines[0].endswith(b'\r\n') else b'\n'
    path.write_bytes(b''.join(lines[:2]) + paragraph.encode('utf-8') + ending * 2 + b''.join(lines[2:]))

manifest_path = c.OUT / 'handoff_manifest.json'
manifest = c.read(manifest_path)
paths = [p for folder in (c.TASK, c.OUT) for p in folder.rglob('*')
         if p.is_file() and '__pycache__' not in p.parts and p != manifest_path]
manifest['files'] = {str(p.relative_to(c.ROOT)): c.sha(p) for p in paths}
manifest['navigation_files'] = {name: c.sha(c.ROOT / name) for name in NAV}
manifest['delivery_checked_utc'] = c.now()
c.put(manifest_path, manifest)
print('Delivery manifest complete; historical navigation bytes preserved')
