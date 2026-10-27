"""Import and synthetic CUDA check before loading any clinical model inputs."""
import json,time,importlib.metadata as md,subprocess
from pathlib import Path
root=Path('/root/autodl-tmp/verifact103');start=time.time()
import unsloth
from unsloth import FastLanguageModel
import torch,transformers,peft
assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
x=torch.ones((32,32),device='cuda',dtype=torch.bfloat16);assert float((x@x)[0,0])==32
versions={n:md.version(n) for n in ['torch','torchvision','triton','xformers','unsloth','unsloth_zoo','transformers','peft','trl']}
subprocess.run([str(root/'venv103/bin/python'),'-m','pip','check'],check=True)
(root/'installed_gpu.lock').write_bytes(subprocess.check_output([str(root/'venv103/bin/python'),'-m','pip','freeze','--all']))
(root/'results/environment_ready.json').write_text(json.dumps(dict(versions=versions,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),BF16=True,seconds=time.time()-start,clinical_inference_executed=False),indent=2))
print(json.dumps(versions),flush=True)
