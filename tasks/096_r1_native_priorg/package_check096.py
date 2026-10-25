"""Bounded publication package review: private fields, links and frozen sources."""
import json,re,subprocess
import common096 as c
O=c.OUT/'valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k'
def main():
    files=[p for root in [c.TASK,c.OUT] for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts];bad=[];sensitive=[];large=[]
    def walk(x,path):
        if isinstance(x,dict):
            for k,v in x.items():
                if k in {'body','messages','proposition','reference','reasoning_content','final_text'}:sensitive.append((str(path.relative_to(c.ROOT)),k))
                walk(v,path)
        elif isinstance(x,list):
            for v in x:walk(v,path)
    for p in files:
        if p.stat().st_size>5_000_000:large.append(str(p))
        if p.suffix in ['.json','.jsonl']:
            data=c.lines(p) if p.suffix=='.jsonl' else c.read(p);walk(data,p)
        if p.suffix in ['.md','.py','.json','.jsonl','.ps1','.csv','.yml']:
            txt=p.read_text(encoding='utf-8-sig')
            if re.search(r'\b(?:sk-[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16})\b',txt):bad.append(str(p.relative_to(c.ROOT)))
    assert not bad and not sensitive and not large,dict(secrets=bad,private_fields=sensitive,large=large)
    src=c.read(c.OUT/'data_freeze.json')['source_sha256']
    for p,h in src.items():assert c.sha(c.ROOT/p)==h,('historic frozen source changed',p)
    assert not subprocess.check_output(['git','diff','--','.gitignore','tasks/085_r1_70b_valdemardi','outputs/085_r1_70b_valdemardi','tasks/095_anchored_minimal_contrast','outputs/095_anchored_minimal_contrast'],cwd=c.ROOT)
    c.put(O/'publication_package_check_final.json',dict(status='PASS',files_checked=len(files),private_data_keys_found=sensitive,secret_patterns_found=bad,large_files_found=large,historical_sources_unchanged=True,scope='executor publication review; not independent audit'))
    exclude={'final_artifact_manifest_v2.json'}
    files=[p for root in [c.TASK,c.OUT] for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    c.put(c.OUT/'final_artifact_manifest_v2.json',dict(status='FINAL_PACKAGE_FROZEN',prior_snapshot_sha256=c.sha(c.OUT/'final_artifact_manifest.json'),amendment='strip generated SVG trailing whitespace; current navigation points to this complete snapshot; no scientific changes',files={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in files if p.name not in exclude},default_unchanged=True,private_receipts_not_in_package=True))
    print('PACKAGE_PASS',len(files))
if __name__=='__main__':main()
