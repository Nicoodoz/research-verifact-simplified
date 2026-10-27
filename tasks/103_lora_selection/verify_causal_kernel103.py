"""Synthetic BF16 forward/backward/update check; no clinical text or labels."""
import json,importlib.metadata as md
from pathlib import Path
import torch
import torch.nn.functional as F
from causal_conv1d import causal_conv1d_fn,causal_conv1d_update
torch.manual_seed(103027)
x=torch.randn(2,256,128,device='cuda',dtype=torch.bfloat16,requires_grad=True)
w=torch.randn(256,4,device='cuda',dtype=torch.bfloat16,requires_grad=True)
b=torch.randn(256,device='cuda',dtype=torch.bfloat16,requires_grad=True)
y=causal_conv1d_fn(x,w,b,activation='silu')
ref=F.silu(F.conv1d(x,w.unsqueeze(1),b,padding=3,groups=256)[...,:128])
torch.testing.assert_close(y,ref,atol=.04,rtol=.04)
g=torch.randn_like(y)
actual=torch.autograd.grad(y,(x,w,b),g,retain_graph=True)
expected=torch.autograd.grad(ref,(x,w,b),g)
for a,e in zip(actual,expected):torch.testing.assert_close(a,e,atol=.5,rtol=.05)
state=torch.randn(2,256,4,device='cuda',dtype=torch.bfloat16);before=state.clone();token=torch.randn(2,256,device='cuda',dtype=torch.bfloat16)
u=causal_conv1d_update(token,state,w.detach(),b.detach(),activation='silu')
rolled=torch.cat([before[:,:,1:],token[:,:,None]],-1)
ur=F.silu((rolled.float()*w.detach().float()).sum(-1)+b.detach().float()).to(torch.bfloat16)
torch.testing.assert_close(u,ur,atol=.04,rtol=.04);torch.testing.assert_close(state,rolled)
result=dict(version=md.version('causal-conv1d'),torch=torch.__version__,abi=torch._C._GLIBCXX_USE_CXX11_ABI,capability=torch.cuda.get_device_capability(),forward_max_abs=float((y-ref).abs().max()),gradient_max_abs=[float((a-e).abs().max()) for a,e in zip(actual,expected)],update_max_abs=float((u-ur).abs().max()),synthetic_only=True)
Path('/root/autodl-tmp/verifact103/results/causal_kernel_check.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
