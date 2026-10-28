"""CPU BF16-autocast regression for the108 attention-reduction dtype fix."""
import argparse
import json
from pathlib import Path
import torch
from torch.nn import functional as F
from model108 import Head,MODES


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path);args=parser.parse_args()
    torch.set_num_threads(4);torch.manual_seed(108029)
    groups=torch.tensor([0,0,0,1,1,2,2,2,2],dtype=torch.long);checks=[]
    for mode in MODES:
        head=Head(mode,hidden_size=8,dropout=0.)
        features=torch.randn(9,8,requires_grad=True)
        observed=[];hook=head.norm.register_forward_hook(lambda module,inputs,output:observed.append(str(output.dtype)))
        with torch.autocast('cpu',dtype=torch.bfloat16):
            logp=head(features,groups)
            separate=torch.stack([head(features[groups==i]) for i in range(3)])
            loss=F.nll_loss(logp,torch.tensor([0,1,2]))
        hook.remove()
        assert logp.dtype==torch.float32 and set(observed)=={'torch.float32'}
        torch.testing.assert_close(logp.exp().sum(-1),torch.ones(3),atol=3e-6,rtol=3e-6)
        torch.testing.assert_close(logp,separate,atol=.004,rtol=.004)
        loss.backward()
        assert bool(torch.isfinite(features.grad).all()) and float(features.grad.abs().sum())>0
        assert all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in head.parameters())
        assert float(head.attention.weight.grad.abs().sum())>0
        if mode!='flat_ce':
            head.zero_grad(set_to_none=True)
            with torch.autocast('cpu',dtype=torch.bfloat16):
                only_NA=F.nll_loss(head(features.detach(),groups),torch.full((3,),2,dtype=torch.long))
            only_NA.backward()
            assert int(head.conditional.weight.grad.count_nonzero())==0
            assert float(head.addressed.weight.grad.abs().sum())>0
            if mode=='hier_pool':assert int(head.conditional_attention.weight.grad.count_nonzero())==0
        with torch.autocast('cpu',enabled=False):
            raw=head.attention(head.norm(features.detach())).squeeze(-1)
            assert raw.dtype==torch.float32 and raw.float().data_ptr()==raw.data_ptr()
        checks.append(dict(arm=mode,probability_normalized=True,single_and_grouped_match=True,
            finite_nonzero_input_and_attention_gradients=True,normalized_features_FP32=True,
            FP32_score_cast_is_noop_without_AMP=True,NA_conditional_gradient_zero=mode!='flat_ce'))
    result=dict(task=108,checks=checks,CPU_autocast='bfloat16',CUDA_initialized=torch.cuda.is_initialized(),
        CUDA_FP16_test_still_required=True,proves_classification_benefit=False)
    assert result['CUDA_initialized'] is False
    if args.output is not None:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
