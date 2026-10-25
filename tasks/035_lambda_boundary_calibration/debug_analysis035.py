import os,sys,traceback,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
TASK=Path(__file__).resolve().parent
sys.path.insert(0,str(TASK))
os.chdir(ROOT)
import common as c
import analysis as a
run=ROOT/'outputs/035_lambda_boundary_calibration/run_001'
datasets=c.read(run/'inputs_numeric.json')
rows=datasets['old_R0']
d=np.load(run/'frozen_predictions/old_R0.npz')
outputs={m:(d[m+'_labels'],d[m+'_logprob']) for m in c.METHODS}
print('loaded',len(rows),list(outputs),flush=True)
try:
    for m,(p,lp) in outputs.items():
        x=a.point(rows,p,lp)
        print('POINT',m,x['correct'],x['NLL'],flush=True)
    b=outputs['U2'];q=outputs['U2_T']
    print('EXTRA',a.paired_extra(rows,b,q),flush=True)
    print('PAIR',c.paired_compare(c.cohort(rows),c.predictions(rows,b[0]),c.predictions(rows,q[0]),iterations=1000)['metrics'],flush=True)
    out=run/'debug_analysis'
    if out.exists(): raise RuntimeError('debug output exists')
    out.mkdir()
    print('CALL ANALYZE',flush=True)
    a.analyze('case',rows,outputs,out)
    print('ANALYZE OK',flush=True)
except BaseException as e:
    msg=''.join(traceback.format_exception(type(e),e,e.__traceback__))
    print(msg,flush=True)
    (run/'debug_analysis_error.txt').write_text(msg,encoding='utf-8')
    raise
