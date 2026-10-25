"""Read-only comparison against pre019 hashes; no clinical text is emitted."""
import common019 as c

def check():
    original=c.read(c.OUT/'history_before.json')['files']
    allowed={'README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md'}
    changed=[]; missing=[]
    for name,expected in original.items():
        path=c.ROOT/name
        if not path.is_file(): missing.append(name)
        elif c.file_hash(path)!=expected: changed.append(name)
    result=dict(created_utc=c.now(),checked_files=len(original),changed=changed,
                missing=missing,non_navigation_changes=sorted(set(changed)-allowed),
                passed=not missing and not(set(changed)-allowed),new_API_calls=0)
    c.write_json(c.OUT/'historical_integrity_001.json',result)
    c.require(result['passed'],'Prior protected files changed')
    print(c.canonical(result),flush=True)

if __name__=='__main__':
    check()
