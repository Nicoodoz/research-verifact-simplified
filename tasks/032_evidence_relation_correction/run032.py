"""Single resumable entry; completed science stages are not silently rerun."""
import argparse,subprocess,sys,traceback
import common032 as c
STAGES=[('prepare032.py','preparation_001/manifest.json'),('nli032.py','nli_001/manifest.json'),('train032.py','inference_001/manifest.json'),('evaluate032.py','analysis_001/manifest.json'),('report032.py','closeout_001/checks.json')]
def main():
    p=argparse.ArgumentParser();p.add_argument('--resume',action='store_true');a=p.parse_args()
    c.OUT.mkdir(parents=True,exist_ok=True)
    if not a.resume and (c.OUT/'preparation_001').exists():raise RuntimeError('Existing task; inspect then use --resume, no overwrite')
    c.require('.local_models' in sys.executable and '032' in sys.executable,'Use task032 virtual environment')
    subprocess.run([sys.executable,str(c.TASK/'test032.py')],cwd=c.ROOT,check=True)
    for script,marker in STAGES:
        if (c.OUT/marker).exists():print('Verified stage marker exists:',marker,flush=True);continue
        subprocess.run([sys.executable,'-u',str(c.TASK/script)],cwd=c.ROOT,check=True)
if __name__=='__main__':
    try:main()
    except Exception:
        c.text(c.OUT/'error_traceback.txt',traceback.format_exc());c.state('failed',state='failed');raise
