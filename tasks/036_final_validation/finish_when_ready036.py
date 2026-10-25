"""Wait for the already launched executor, then run offline closeout once."""
import argparse,ctypes,subprocess,sys,traceback,time
import common036 as c
def main(wait_pid):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p;kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    handle=kernel.OpenProcess(0x00100000,False,wait_pid)
    if handle:
        c.put(c.OUT/'closeout_status.json',dict(state='waiting_for_API_executor',executor_pid=wait_pid,updated_utc=c.now()))
        try:
            while kernel.WaitForSingleObject(handle,50000)==0x102:pass
        finally:kernel.CloseHandle(handle)
    assert c.read(c.OUT/'CALLS_STATUS.json')['stage']=='all','API executor did not complete'
    steps=['integrity036.py','predict036.py','evaluate036.py','costs036.py','correct_accounting036.py','plots036.py','final_review036.py','report036.py']
    for name in steps:
        c.put(c.OUT/'closeout_status.json',dict(state='running_offline_stage',stage=name,updated_utc=c.now()));print('036 closeout',name,flush=True)
        subprocess.run([sys.executable,'-u','-B',str(c.TASK/name)],cwd=c.ROOT,check=True)
    c.put(c.OUT/'closeout_status.json',dict(state='self_verification',updated_utc=c.now()))
    subprocess.run([sys.executable,'-u','-B',str(c.TASK/'verify036.py'),'--output','outputs/replays/036_check_001'],cwd=c.ROOT,check=True)
    c.put(c.OUT/'closeout_status.json',dict(state='reports_and_selfcheck_ready_for_executor_review',updated_utc=c.now(),independent_audit='pending',push_not_yet_performed=True))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait-pid',type=int,required=True);args=p.parse_args()
    try:main(args.wait_pid)
    except BaseException as exc:
        c.put(c.OUT/('closeout_error_'+str(time.time_ns())+'.json'),dict(created_utc=c.now(),exception_type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()));traceback.print_exc();sys.exit(1)
