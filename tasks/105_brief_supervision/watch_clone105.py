"""Bounded guard for the user-designated clone; never reaches the original."""
from pathlib import Path
import json,os,socket,subprocess,time
root=Path('/root/105_control');host='autodl-container-jnb93wme4w-cae1e260'
assert socket.gethostname()==host
start=1793158200.0 # user: 2026-10-28 11:30 +08:00
price=6.98;prior=.05494024872117573
prep_deadline=1793160589.0 # first successful contact03:54:49UTC +15min
root.mkdir(exist_ok=True)
def put(name,value):
    path=root/name;temp=path.with_suffix('.tmp');temp.write_text(json.dumps(value,indent=2)+'\n');temp.replace(path)
lock=root/'watch_clone.pid';fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.write(fd,str(os.getpid()).encode());os.close(fd)
while True:
    assert socket.gethostname()==host
    now=time.time();used=prior+(now-start)/3600*price
    reason=None
    if (root/'finish_requested.json').exists():reason='explicit_finish'
    elif now>=start+145*60:reason='save_shutdown_margin_before150min'
    elif used>=18:reason='18cny_operating_line'
    elif now>=prep_deadline and not (root/'GPU_ready.json').exists():reason='preparation_not_ready_within15min'
    put('watch_heartbeat.json',dict(pid=os.getpid(),epoch=now,billing_start=start,price=price,known_prior_min_cny=prior,
        estimated_used_cny=used,reserve_cny=2,cap_cny=20,GPU_hard_limit_seconds=9000,hostname=host,reason=reason))
    if reason:
        receipt=dict(request_epoch=now,reason=reason,estimated_known_compute_cny=used,GPU_elapsed_seconds=now-start,
            platform_stop_confirmed=False,original_instance_untouched=True)
        put('shutdown_requested.json',receipt);os.sync()
        program=Path('/usr/bin/shutdown')
        with program.open('rb') as handle:magic=handle.read(4)
        command=([] if magic.startswith((b'#!',b'\x7fELF')) else ['/bin/bash'])+[str(program),'-h','now']
        for attempt in range(3):
            try:
                result=subprocess.run(command,capture_output=True,text=True,timeout=25)
                put('shutdown_result.json',dict(receipt,attempt=attempt+1,command=command,returncode=result.returncode,
                    stdout=result.stdout,stderr=result.stderr));os.sync()
                if result.returncode==0:raise SystemExit(0)
            except (OSError,subprocess.TimeoutExpired) as exc:put('shutdown_error.json',dict(receipt,error=str(exc)))
            time.sleep(3)
        raise RuntimeError('Platform shutdown failed; console confirmation required')
    time.sleep(2)
