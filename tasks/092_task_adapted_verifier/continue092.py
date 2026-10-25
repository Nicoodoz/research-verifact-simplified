"""Sequential, restartable offline pipeline; no API calls or automatic next research task."""
import subprocess,sys
import common092 as c
def run(name):
    print('RUN',name,flush=True);subprocess.run([sys.executable,'-u',str(c.TASK/name)],cwd=c.ROOT,check=True)
def main():
    assert not (c.OUT/'completion.json').exists(),'092 complete: use analysis-only reproduction or a separately authorized isolated retraining checkout.'
    assert not (c.TASK/'PAUSED_BY_USER.md').exists(),'092 paused by user: obtain explicit resume instruction and archive the pause marker before running.'
    assert (c.OUT/'c48_manifest.json').exists(),'Complete local_c48.py first; never launch a duplicate runner.'
    if not (c.OUT/'cache_manifest.json').exists():run('cache092.py')
    assert c.read(c.OUT/'cache_manifest.json')['complete']
    run('freeze092.py');run('train092.py')
    # Analysis uses the CPU/API environment through the established activation wrapper.
    subprocess.run(['pwsh','-NoProfile','-File',str(c.ROOT/'scripts/run_research.ps1'),str(c.TASK/'analyze092.py')],cwd=c.ROOT,check=True)
    print('OOF and main analysis complete. Review real results for conditional fusion/report; no automatic 093.',flush=True)
if __name__=='__main__':main()
