"""Resume only after user confirms GPU shutdown; never calls endpoint."""
import argparse,socket,sys
from unittest.mock import patch
import common096 as c
import marlin096 as m
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--gpu-shutdown-confirmed',action='store_true');a=ap.parse_args()
    assert a.gpu_shutdown_confirmed,'WAIT_FOR_USER_GPU_SHUTDOWN_CONFIRMATION'
    m.activate();done=c.read(m.O/'R1_INFERENCE_DONE.json');assert done['status']=='R1_INFERENCE_DONE'
    for j in m.r.jobs():
        d=m.r.success(j)
        if d:assert c.read(d/'receipt.json')['backend_id']==m.BACKEND
    src=m.OLD_P/'comparator_cache.jsonl';dst=m.P/'comparator_cache.jsonl'
    if dst.exists():assert dst.read_bytes()==src.read_bytes()
    else:dst.write_bytes(src.read_bytes())
    import live_analyze096 as analysis
    analysis.O=m.O;analysis.P=m.P;analysis.main()
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Offline after shutdown')):main()
