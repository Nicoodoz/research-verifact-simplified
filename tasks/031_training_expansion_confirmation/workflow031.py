"""Wait on the current retrieval process once, then run fixed remaining stages."""
import argparse,ctypes,subprocess,sys,traceback
import common031 as c
def main(wait_pid):
    try:
        if wait_pid:
            kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p;kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            handle=kernel.OpenProcess(0x00100000,False,wait_pid)
            if handle:
                c.put(c.OUT/'workflow_status.json',dict(state='waiting_for_existing_retrieval',pid=wait_pid,updated_utc=c.now()));print('Waiting on existing retrieval process',wait_pid,flush=True);kernel.WaitForSingleObject(handle,0xFFFFFFFF);kernel.CloseHandle(handle)
        import api031 as a
        _,term,_=a.state();jobs=c.lines(c.OUT/'retrieval_001/jobs.jsonl');c.require(all(j['request_id'] in term and term[j['request_id']]['parsed']['status']=='success' for j in jobs),'Retrieval incomplete; do not silently continue')
        c.put(c.OUT/'workflow_status.json',dict(state='running_fixed_remaining_stages',updated_utc=c.now()));subprocess.run([sys.executable,'-u','-B',str(c.TASK/'continue031.py')],cwd=c.ROOT,check=True);c.put(c.OUT/'workflow_status.json',dict(state='calls_inference_evaluation_complete',updated_utc=c.now(),report_and_audit_handoff_pending=True))
    except BaseException as exc:
        c.put(c.OUT/'workflow_error.json',dict(created_utc=c.now(),type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc(),no_automatic_research_change=True));traceback.print_exc();return 1
    return 0
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--wait-pid',type=int);sys.exit(main(p.parse_args().wait_pid))
