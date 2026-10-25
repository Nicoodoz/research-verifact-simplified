"""Final deliverable integrity and local credential exclusion; zero network."""
import subprocess
from common087 import *

def main():
    required=('report.md','analysis.json','predictions.jsonl','selfcheck.json','cost_ledger.json','performance_tables.md','cost_tables.md','086_correction.md','audit_handoff.md')
    assert all((OUT/p).is_file() for p in required)
    assert read(OUT/'selfcheck.json')['status']=='PASS'
    assert not (OUT/'run.lock').exists()
    destination=OUT/'delivery_manifest.json'
    temporary=OUT/'delivery_manifest.tmp'
    assert not temporary.exists()
    paths=sorted([p for folder in (TASK,OUT) for p in folder.rglob('*') if p.is_file() and p!=destination])
    assert all(p.stat().st_size<95_000_000 for p in paths)
    # Read credential values locally only; never print/write them or their hashes.
    secrets=[]
    for envname in ('.env.aliyun','.env.siliconflow_pool'):
        p=ROOT/envname
        if p.exists():
            for line in p.read_text(encoding='utf-8-sig').splitlines():
                if '=' not in line or line.lstrip().startswith('#'):continue
                key,value=line.split('=',1);value=value.strip().strip('\"\'')
                if ('KEY' in key.upper() or 'TOKEN' in key.upper()) and len(value)>=12:secrets.append(value.encode())
    for p in paths:
        data=p.read_bytes()
        if any(v in data for v in secrets):raise RuntimeError('credential detected in deliverable')
        assert not data.startswith(b'\xef\xbb\xbf'),'new files must be UTF8 without BOM'
    result=dict(status='PASS',created_utc=now(),independent_audit=False,credential_value_scan='PASS',
        files=len(paths),total_bytes=sum(p.stat().st_size for p in paths),largest_bytes=max(p.stat().st_size for p in paths),
        contents_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in paths})
    # This non-scientific export manifest is refreshable; frozen inputs/results are not.
    put(temporary,result)
    temporary.replace(destination)
    print(canonical({k:v for k,v in result.items() if k!='contents_sha256'}))

if __name__=='__main__':main()
