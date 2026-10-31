"""Check new auxiliary CE math and its gradient, not classifier effectiveness."""
from pathlib import Path
import sys,json
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/138_rationale_tasks'))
import torch
from torch.nn import functional as F
from loss138 import answer_hidden_loss
torch.manual_seed(138031)
head=torch.nn.Linear(7,19,bias=False).double();head.requires_grad_(False)
hidden=torch.randn(1,9,7,dtype=torch.double,requires_grad=True);ids=torch.randint(0,19,(1,9));groups=torch.tensor([[0,0,0,0,1,1,1,1,1]])
value,info=answer_hidden_loss(hidden,head,ids,groups,chunk_tokens=2)
selected=groups[:,1:]>0;expected=F.cross_entropy(head(hidden[:,:-1,:][selected]).float(),ids[:,1:][selected])
g1=torch.autograd.grad(value,hidden,retain_graph=True)[0];g2=torch.autograd.grad(expected,hidden)[0]
assert torch.allclose(value,expected,atol=1e-6) and torch.allclose(g1,g2,atol=1e-6)
result=dict(scope='new auxiliary CE only',loss_matches_direct_CE=True,gradient_matches_direct_CE=True,answer_tokens=info['answer_tokens'],classification_effect_tested=False)
p=R/'outputs/138_rationale_tasks/auxiliary_loss_check.json';p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
