"""Run manually on the rented Linux host; local inspection, no downloads.

Do NOT execute this script on the current local machine as a service probe.
The resulting JSON is private runtime metadata; never includes API credentials.
"""
import argparse,json,hashlib,subprocess,importlib.metadata,os
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def version(n):
    try:return importlib.metadata.version(n)
    except importlib.metadata.PackageNotFoundError:return None
def redact(command):
    import re
    command=re.sub(r'(?i)(--(?:api-key|token)(?:=|\s+))(\S+)',r'\1<REDACTED>',command)
    return re.sub(r'(?i)((?:HF_TOKEN|HUGGING_FACE_HUB_TOKEN|OPENAI_API_KEY|AWS_SECRET_ACCESS_KEY|AWS_SESSION_TOKEN)=)(\S+)',r'\1<REDACTED>',command)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--model-path',required=True);ap.add_argument('--repository',required=True);ap.add_argument('--revision',required=True);ap.add_argument('--revision-provider',choices=['HuggingFace','ModelScope','local'],required=True);ap.add_argument('--server-command',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
    root=Path(a.model_path).resolve();config=json.loads((root/'config.json').read_text());command=redact(a.server_command)
    import torch,shlex
    args=shlex.split(a.server_command);max_len=None
    for i,arg in enumerate(args):
        if arg.startswith('--max-model-len='):max_len=int(arg.split('=',1)[1])
        elif arg=='--max-model-len' and i+1<len(args):max_len=int(args[i+1])
    gpu=subprocess.run(['nvidia-smi','--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.strip().splitlines()
    result=dict(model_repository=a.repository,resolved_revision=a.revision,revision_provider=a.revision_provider,model_path=str(root),vllm_version=version('vllm'),torch_version=version('torch'),cuda_version=torch.version.cuda,gpu_inventory=gpu,server_command=command,max_model_len=max_len,quant_method=config.get('quantization_config',{}).get('quant_method'),quantization=config.get('quantization_config'),files={n:sha(root/n) for n in ['config.json','tokenizer.json','tokenizer_config.json']},weight_inventory=[dict(name=p.name,bytes=p.stat().st_size) for p in sorted(root.glob('*.safetensors'))],weight_bytes_hashed=False,revision_note='User-supplied source revision; ModelScope and HuggingFace revisions are not assumed equal. Directory name/service alias alone is not weight authentication.',environment={k:os.environ.get(k) for k in ['VLLM_USE_V1','CUDA_VISIBLE_DEVICES','HF_HOME']})
    out=Path(a.output)
    with out.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print('Private server manifest saved',out)
if __name__=='__main__':main()
