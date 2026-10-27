"""Run only on the supplied task instance after billing guard starts."""
import argparse,json,hashlib
from pathlib import Path
def main():
 from huggingface_hub import snapshot_download
 p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--model-root',type=Path,required=True);a=p.parse_args()
 meta=json.loads((a.bundle/'model_metadata.json').read_text());plan=json.loads((a.bundle/'gpu_plan.json').read_text())
 for name in plan['candidates']:
  m=meta[name];dest=a.model_root/name
  snapshot_download(repo_id=m['repo'],revision=m['revision'],local_dir=dest,allow_patterns=['*.json','*.jinja','*.safetensors','*.txt','*.model'])
  for f in ['config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja']:assert hashlib.sha256((dest/f).read_bytes()).hexdigest()==m['files'][f]['sha256']
  (dest/'REVISION').write_text(m['revision']+'\n')
if __name__=='__main__':main()
