"""Check final navigation, UTF-8 artifacts and protected history without mutation."""
import re
from pathlib import Path
import common018 as c
from verify018 import NAV

if __name__=='__main__':
    files=[p for base in (c.TASK,c.OUT) for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    missing=[]
    for p in files:
        c.require(not p.read_bytes().startswith(b'\xef\xbb\xbf'),'New BOM: '+str(p))
        if p.suffix!='.md' or 'verification_001' in p.parts or 'diagnosis_001' in p.parts:continue
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            target=(p.parent/link.split('#')[0]).resolve()
            if target==c.OUT/'handoff_001.json' and not target.exists():continue
            if not target.exists():missing.append(dict(file=p.relative_to(c.ROOT).as_posix(),link=link))
    c.require(not missing,'Broken links: '+c.canonical(missing))
    hist=c.read(c.OUT/'history_before.json');changed=[]
    for p,h in hist['files'].items():
        if p not in NAV:c.require(c.file_hash(c.ROOT/p)==h,'Historical change: '+p)
        elif c.file_hash(c.ROOT/p)!=h:changed.append(p)
    print(c.canonical(dict(checked_files=len(files),missing_links=missing,navigation_changes=changed,largest=[dict(path=p.relative_to(c.ROOT).as_posix(),bytes=p.stat().st_size) for p in sorted(files,key=lambda p:p.stat().st_size,reverse=True)[:4]],total_bytes=sum(p.stat().st_size for p in files))))
