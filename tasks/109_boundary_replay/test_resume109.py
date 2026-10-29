"""Tiny CPU continuation50->new0->new24; never opens a9B weight tensor."""
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import common109 as c

def run():
    import torch
    from safetensors.torch import save_file,load_file
    sys.path.insert(0,str(c.ROOT/'tasks/107_support_aux'));import checkpoint107 as checkpoint
    sys.path.insert(0,str(c.ROOT/'tasks/105_brief_supervision'));from data105 import training_plan,validate_cursor
    class Tiny(torch.nn.Module):
        def __init__(self):super().__init__();self.weight=torch.nn.Parameter(torch.tensor([.2,-.3]))
        def save_pretrained(self,folder,**kwargs):save_file(self.state_dict(),str(Path(folder)/'adapter_model.safetensors'))
    def setup():
        net=Tiny();optimizer=torch.optim.AdamW(net.parameters(),lr=1e-4,weight_decay=0.)
        scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lr_lambda=lambda step:1.)
        return net,optimizer,scheduler
    def update(net,optimizer,scheduler):
        optimizer.zero_grad();((net.weight-1)**2).sum().backward();optimizer.step();scheduler.step()
    with TemporaryDirectory(prefix='109-tiny-resume-') as temporary:
        root=Path(temporary);model,optimizer,scheduler=setup()
        for _ in range(50):update(model,optimizer,scheduler)
        source_fp=dict(task=107,arm='label_only',unit_fixture=True)
        checkpoint.save(model,optimizer,scheduler,root/'source',50,392,source_fp)
        continued,opt,sch=setup()
        def restore(folder):continued.load_state_dict(load_file(str(folder/'adapter_model.safetensors')))
        step,consumed,_=checkpoint.load(opt,sch,root/'source',source_fp,restore)
        assert (step,consumed)==(50,392) and sch.last_epoch==50
        torch.testing.assert_close(continued.weight,model.weight,rtol=0,atol=0)
        assert all(int(value['step'])==50 for value in opt.state.values())
        new_fp=dict(task=109,arm='boundary_replay',source='unit_source50',unit_fixture=True)
        checkpoint.save(continued,opt,sch,root/'new109',0,0,new_fp)
        plan=training_plan([str(i) for i in range(192)],1,8);assert len(plan)==24
        for entry in plan[:5]:
            update(continued,opt,sch)
            checkpoint.save(continued,opt,sch,root/'new109',entry['step'],entry['consumed'],new_fp)
        state=continued.weight.detach().clone();restored,op2,sc2=setup()
        def restore2(folder):restored.load_state_dict(load_file(str(folder/'adapter_model.safetensors')))
        step,consumed,_=checkpoint.load(op2,sc2,root/'new109',new_fp,restore2)
        assert (step,consumed,sc2.last_epoch)==(5,40,55);torch.testing.assert_close(restored.weight,state,rtol=0,atol=0)
        for entry in validate_cursor(plan,step,consumed):update(restored,op2,sc2)
        assert sc2.last_epoch==74 and all(int(v['step'])==74 for v in op2.state.values())
        assert c.read(root/'source/resume.json')['step']==50
    assert not torch.cuda.is_initialized()
    result=dict(task=109,tiny_CPU_test=True,real9B_weights_loaded=False,source_step50_optimizer_preserved=True,
        new_data_cursor_starts0=True,new_cursor_resume5_40=True,final_scheduler_and_Adam_step74=True,
        source_checkpoint_unchanged=True,old107_atomic_helper_reused=True,CUDA_initialized=False,
        clinical_effect_demonstrated=False,real_GPU9B_resume_not_retested=True)
    c.put(c.OUT/'continuation_cpu_check.json',result);print(c.canonical(result))

if __name__=='__main__':run()
