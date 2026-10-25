"""Task-local Windows atomic-replace retry; preserve old029 writer/source bytes."""
import ctypes,json,os,time
from pathlib import Path
import common031 as c
def install():
    original=c.base.write_text
    if getattr(original,'_031_safe',False):return
    def safe(path,text):
        path=Path(path)
        for attempt in range(20):
            try:return original(path,text)
            except PermissionError:
                if attempt<19:time.sleep(min(.05*2**attempt,1.));continue
                if path.name in ('execution_status.json','workflow_status.json'):
                    event=c.OUT/'io_events'/f'{time.time_ns()}.json';event.parent.mkdir(parents=True,exist_ok=True);event.write_text(json.dumps(dict(path=str(path),error='status_replace_permission_after20_attempts',nonfatal=True)),encoding='utf-8');return
                raise
    safe._031_safe=True;c.base.write_text=safe;c.write_text=safe
def register():
    out=c.OUT/'io_amendment_001'
    if out.exists():
        c.require(c.read(out/'manifest.json')['wrapper_sha256']==c.sha(c.TASK/'safe_io031.py'),'IO wrapper changed');return
    out.mkdir();tmp=c.OUT/'execution_status.json.tmp';status=c.OUT/'execution_status.json'
    for path in (tmp,status):
        if path.exists():(out/path.name).write_bytes(path.read_bytes())
    missing=[str(p.relative_to(c.ROOT)) for p in (c.OUT/'attempts').glob('*/request.json') if not (p.parent/'receipt.json').exists()]
    # Synthetic demonstration: a read handle without FILE_SHARE_DELETE blocks replace.
    test=out/'synthetic_locked_file.txt';test.write_text('original',encoding='utf-8');kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_void_p];kernel.CreateFileW.restype=ctypes.c_void_p;kernel.CloseHandle.argtypes=[ctypes.c_void_p];handle=kernel.CreateFileW(str(test),0x80000000,1,None,3,0,None);c.require(handle not in (None,ctypes.c_void_p(-1).value),'Synthetic lock failed');raised=False
    try:
        try:c.base.write_text(test,'replacement')
        except PermissionError:raised=True
    finally:kernel.CloseHandle(handle)
    c.require(raised,'Could not reproduce replace-sharing failure');install();c.write_text(test,'replacement');c.require(test.read_text()=='replacement','Replacement after release failed')
    c.put(out/'manifest.json',dict(created_utc=c.now(),reason='Score status remained893 while intact execution_status.json.tmp had894; Windows progress-file atomic replacement failed. Old writer sharing failure reproduced synthetically.',before_writer_source=c.sha(c.base.TASK/'common029.py'),wrapper_sha256=c.sha(c.TASK/'safe_io031.py'),unknown_request_paths=missing,unknown_n=len(missing),saved_successes_unchanged=True,API_calls_in_this_check=0,changes_only='Retry Windows PermissionError; progress/status failure after retries is nonfatal; no scientific definition change'))
