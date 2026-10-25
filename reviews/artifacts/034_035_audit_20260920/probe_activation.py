
from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parents[3];out=Path(__file__).parent
script=str(root/'tasks/035_lambda_boundary_calibration/scipy_test035.py')
commands={
 'unactivated_absolute_python':['E:/miniconda3/envs/research-verifact-029/python.exe','-B',script],
 'conda_activated_same_python':['E:/miniconda3/Scripts/conda.exe','run','--no-capture-output','-n','research-verifact-029','python','-B',script]}
result={}
for name,cmd in commands.items():
 p=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=60)
 result[name]=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
assert result['unactivated_absolute_python']['returncode']!=0
assert result['conda_activated_same_python']['returncode']==0
(out/'activation_comparison.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print('Same environment: unactivated fails; conda-activated succeeds.')
