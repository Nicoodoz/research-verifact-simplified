import sys,platform,importlib.metadata as md,subprocess
import common092 as c
def main():
    import torch
    files=['config.json','protocol.md','model092.py','train092.py','cache092.py','folds092.py']
    obj=dict(utc=c.now(),head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),code={f:c.sha(c.TASK/f) for f in files},cohort_sha256=c.sha(c.OUT/'cohort.jsonl'),folds_sha256=c.sha(c.OUT/'folds.json'),inputs_sha256=c.sha(c.PRIVATE/'inputs.jsonl'),environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),packages={p:md.version(p) for p in ['torch','transformers','numpy','scikit-learn','safetensors']},GPU=torch.cuda.get_device_name(0),GPU_bytes=torch.cuda.get_device_properties(0).total_memory),API_cap_cny=30,API_spent_cny=0)
    path=c.OUT/('training_freeze_v3.json' if (c.OUT/'training_numeric_fix.json').exists() else 'training_freeze_v2.json' if (c.OUT/'cache_config_compatibility.json').exists() else 'training_freeze.json')
    if path.exists():
        old=c.read(path)
        for key in ['code','cohort_sha256','folds_sha256','inputs_sha256']:assert old[key]==obj[key],key
    else:c.put(path,obj)
    print('Training freeze verified',flush=True)
if __name__=='__main__':main()
