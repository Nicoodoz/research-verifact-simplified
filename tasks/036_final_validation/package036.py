"""Lossless gzip transport for task files above GitHub's practical file-size limit."""
import argparse,gzip,hashlib,shutil
from pathlib import Path
import common036 as c
def pack():
    records=[]
    for path in sorted(c.OUT.rglob('*')):
        if not path.is_file() or path.suffix=='.gz' or path.stat().st_size<90*1024*1024:continue
        zipped=path.with_name(path.name+'.gz');assert not zipped.exists()
        with path.open('rb') as src,zipped.open('xb') as stream,gzip.GzipFile(filename='',mode='wb',fileobj=stream,mtime=0) as dst:shutil.copyfileobj(src,dst)
        h=hashlib.sha256()
        with gzip.open(zipped,'rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        assert h.hexdigest()==c.sha(path)
        records.append(dict(original=str(path.relative_to(c.ROOT)),gzip=str(zipped.relative_to(c.ROOT)),original_sha256=h.hexdigest(),gzip_sha256=c.sha(zipped),original_bytes=path.stat().st_size,gzip_bytes=zipped.stat().st_size,original_local_file_retained=True))
    c.put(c.OUT/'artifact_packages.json',dict(created_utc=c.now(),reason='Lossless transport only; no scientific or raw HTTP byte edits; original large local files not staged, gzip equivalents staged; .gitignore unchanged',files=records));print('Packed large files',len(records))
def restore():
    for r in c.read(c.OUT/'artifact_packages.json')['files']:
        path=c.ROOT/r['original'];zipped=c.ROOT/r['gzip'];assert path.resolve().is_relative_to(c.OUT) and zipped.resolve().is_relative_to(c.OUT)
        assert c.sha(zipped)==r['gzip_sha256']
        if path.exists():assert c.sha(path)==r['original_sha256'];continue
        with gzip.open(zipped,'rb') as src,path.open('xb') as dst:shutil.copyfileobj(src,dst)
        assert c.sha(path)==r['original_sha256']
    print('All transport packages restored/verified; no API')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['pack','restore']);args=p.parse_args();pack() if args.action=='pack' else restore()
