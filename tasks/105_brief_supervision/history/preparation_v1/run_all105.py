"""Next-stage serial supervisor. Inert until explicitly run on the GPU host."""
from pathlib import Path
import argparse
import os
import subprocess
import sys
import common105 as c
import budget105 as budget
from verify105 import bundle as verify_bundle

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--model-dir',type=Path,required=True);p.add_argument('--ledger',type=Path,required=True);a=p.parse_args()
    if os.name=='nt':raise RuntimeError('This is a future Linux GPU-host supervisor, not the local preparation command')
    verify_bundle(a.bundle);budget.require(a.ledger,300,watchdog=True)
    a.work.mkdir(parents=True,exist_ok=True)
    lock=a.work/'supervisor.lock'
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(descriptor,str(os.getpid()).encode());os.close(descriptor)
    script=a.bundle/'tasks/105_brief_supervision/worker105.py'
    common=['--bundle',str(a.bundle),'--work',str(a.work),'--model-dir',str(a.model_dir),'--ledger',str(a.ledger)]
    try:
        gate=a.work/'gpu_gate.json'
        if not gate.exists():subprocess.run([sys.executable,'-u',str(script),*common,'--mode','gate'],check=True)
        for arm in c.ARMS[1:]:
            folder=a.work/'train'/arm
            if (folder/'training_done.json').exists():
                done=c.read(folder/'training_done.json')
                assert done['step']==50 and done['consumed']==392 and done['fingerprint']['bundle_manifest_sha256']==c.sha(a.bundle/'manifest.json')
                continue
            resume=['--resume'] if (folder/'resume.json').exists() else []
            subprocess.run([sys.executable,'-u',str(script),*common,'--mode','train','--arm',arm,*resume],check=True)
        for arm in c.ARMS:
            subprocess.run([sys.executable,'-u',str(script),*common,'--mode','eval','--arm',arm],check=True)
        c.put(a.work/'execution_complete.json',dict(train_samples_per_arm=392,optimizer_steps_per_arm=50,
            expected_eval_per_arm=500,arms=list(c.ARMS),bundle_sha256=c.sha(a.bundle/'manifest.json'),classification_metrics_not_inspected=True))
    finally:
        # Success or failure cannot leave an idle GPU burning the remaining cap.
        c.put(a.ledger.parent/'finish_requested.json',dict(utc=c.utc(),reason='supervisor_finished_or_failed',remote_platform_stop_must_be_verified=True))
        lock.unlink()

if __name__=='__main__':main()
