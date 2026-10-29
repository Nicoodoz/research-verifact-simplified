"""Targeted numerical check of reused106 objective; tiny CPU tensors only."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/106_label_preparation'));from loss106 import segmented_sum_loss
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
import torch
from torch.nn import functional as F
def main():
 torch.manual_seed(115);results=[]
 for n in [1,2,3]:
  size=4+n+6;h=torch.randn(1,size,5,dtype=torch.float64,requires_grad=True);head=torch.nn.Linear(5,11,bias=False,dtype=torch.float64);head.requires_grad_(False);ids=torch.arange(size).remainder(11)[None];groups=torch.tensor([[0]*4+[1]*n+[2]*6])
  loss,info=segmented_sum_loss(h,head,ids,groups,360/196,chunk_tokens=2,checkpoint_head=True)
  targets=ids[:,1:];kinds=groups[:,1:];selected=kinds>0;ce=F.cross_entropy(head(h[:,:-1,:][selected]).float(),targets[selected],reduction='none');expected=ce[kinds[selected]==1].sum()/(360/196)+ce[kinds[selected]==2].mean()
  assert torch.allclose(loss,expected,atol=1e-6)
  grad=torch.autograd.grad(loss,h,retain_graph=True)[0];reference=torch.autograd.grad(expected,h)[0];assert torch.allclose(grad,reference,atol=1e-6)
  assert info['verdict_tokens']==n and not grad[0,-1].any() and not grad[0,:3].any()
  results.append(dict(label_tokens=n,loss_equal=True,gradient_equal=True,causal_shift=True,head_frozen=True))
 # This counterexample demonstrates a property of the objective, not clinical efficacy.
 p=[83/196,62/196,51/196];weighted=[x/l for x,l in zip(p,[1,2,3])];q=[x/sum(weighted) for x in weighted]
 c.put(R/'outputs/115_label_sum/cpu_checks.json',dict(PASS=True,numerical=results,weights_per_label_token=196/360,average_segment_weight=(83+2*62+3*51)/196/(360/196),toy_identical_input_ground_truth_distribution=p,toy_mean_optimum_class_distribution=q,toy_sum_optimum_class_distribution=p,toy_requires_indistinguishable_input=True,not_claim_of_learned_9B_prior=True,not_real_classification_benefit=True,no_GPU_initialized=not torch.cuda.is_initialized()))
 print('PASS: reused106 loss equals direct formula and causal gradients for all three token lengths; CPU only')
if __name__=='__main__':main()
