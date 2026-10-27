"""Resume unchanged text batches while keeping UNUSED vision weights off GPU."""
import gpu_batch103 as batch
gw=batch.gw;original_load=gw.load
def load(a):
 model,tok,Fast,torch=original_load(a)
 assert a.model=='qwen3.6-35b-a3b' and a.phase=='eval' and a.arm=='lora_label'
 vision=[(n,m) for n,m in model.named_modules() if n.endswith('.visual')]
 assert len(vision)==1,'Inspect architecture; never move an active text module'
 name,module=vision[0];size=sum(p.numel()*p.element_size() for p in module.parameters());module.to('cpu')
 # Keep model.device (first registered parameter) on the active text device;
 # otherwise Accelerate can place input indices on CPU when wrapping PEFT.
 parent_name,leaf=name.rsplit('.',1);parent=model.get_submodule(parent_name)
 parked=parent._modules.pop(leaf);parent._modules[leaf]=parked
 assert next(model.parameters()).device.type=='cuda'
 def forbidden(*args,**kwargs):raise RuntimeError('Vision unexpectedly invoked: abort rather than silently offload computation')
 module.register_forward_pre_hook(forbidden)
 assert all(p.device.type=='cuda' for n,p in model.named_parameters() if not n.startswith(name+'.'))
 torch.cuda.empty_cache()
 gw.write(a.work/'unused_vision_memory_adjustment.json',dict(module=name,bytes_released=size,text_weights_on_cuda=True,vision_forward_forbidden=True,batch_input_precision_and_decoding_unchanged=True,reason='Resume12 OOM cases without repeating completed answers or changing paired batches'))
 return model,tok,Fast,torch
if __name__=='__main__':gw.load=load;gw.inference=batch.inference;gw.main()
