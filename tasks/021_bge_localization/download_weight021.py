"""Robust ranged downloader for >2 GiB public HF LFS files."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse, hashlib, math, os, subprocess, time

def download_part(i,start,end,folder,url,proxy):
    part=folder/f'part{i:02d}.bin'; tmp=folder/f'part{i:02d}.chunk'
    expected=end-start+1
    if part.exists() and part.stat().st_size>expected:
        raise ValueError(f'part {i} too large')
    attempts=0
    while (part.stat().st_size if part.exists() else 0)<expected:
        have=part.stat().st_size if part.exists() else 0
        lo=start+have; attempts+=1
        if tmp.exists(): tmp.unlink()
        cmd=['curl.exe','-L','--fail','-x',proxy,'-r',f'{lo}-{end}','-o',str(tmp),url]
        proc=subprocess.run(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        got=tmp.stat().st_size if tmp.exists() else 0
        if got:
            if have+got>expected: raise ValueError(f'part {i} overflow')
            with part.open('ab') as out, tmp.open('rb') as src:
                while True:
                    block=src.read(8*1024*1024)
                    if not block: break
                    out.write(block)
            tmp.unlink()
            print(f'PART {i} {part.stat().st_size}/{expected} attempt={attempts}',flush=True)
        else:
            time.sleep(min(5,attempts))
            if attempts>=30: raise RuntimeError(f'part {i} stalled rc={proc.returncode}')
    return part

def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(16*1024*1024),b''): h.update(block)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--url',required=True); ap.add_argument('--size',type=int,required=True)
    ap.add_argument('--sha256',required=True); ap.add_argument('--output',required=True)
    ap.add_argument('--parts',type=int,default=8)
    ap.add_argument('--proxy',default='http://127.0.0.1:12450')
    a=ap.parse_args(); target=Path(a.output); folder=target.parent
    folder.mkdir(parents=True,exist_ok=True)
    chunk=math.ceil(a.size/a.parts)
    ranges=[]
    for i in range(a.parts):
        start=i*chunk; end=min(a.size-1,(i+1)*chunk-1)
        if start<=end: ranges.append((i,start,end))
    with ThreadPoolExecutor(max_workers=len(ranges)) as pool:
        fs=[pool.submit(download_part,i,s,e,folder,a.url,a.proxy) for i,s,e in ranges]
        parts=[f.result() for f in fs]
    with target.open('wb') as out:
        for part in sorted(parts):
            with part.open('rb') as src:
                while True:
                    block=src.read(16*1024*1024)
                    if not block: break
                    out.write(block)
    if target.stat().st_size!=a.size: raise ValueError('assembled size mismatch')
    actual=sha256(target)
    if actual!=a.sha256: raise ValueError(f'SHA mismatch {actual}')
    print(f'VALID {target} size={a.size} sha256={actual}',flush=True)

if __name__=='__main__':
    main()
