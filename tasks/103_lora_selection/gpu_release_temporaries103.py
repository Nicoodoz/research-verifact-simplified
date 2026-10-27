"""Inference-only lifetime fix: release dead MoE tensors before final reduction."""
import inspect,sys,hashlib
import gpu_batch103 as batch
gw=batch.gw;original_load=gw.load;patched=[]
def load(a):
 model,tok,Fast,torch=original_load(a)
 assert a.model=='qwen3.6-35b-a3b' and a.phase=='eval' and a.arm=='lora_label'
 for name,module in list(sys.modules.items()):
  if not name.endswith('moe_utils') or not hasattr(module,'forward_triton_grouped_gemm'):continue
  fn=module.forward_triton_grouped_gemm
  source=inspect.getsource(inspect.unwrap(fn));anchor='    top_k_weights_casted = top_k_weights.to(hidden_states.dtype)'
  assert source.count(anchor)==1
  insertion='''    # All uses of these temporaries have finished. No arithmetic is changed.
    # Never release autograd intermediates in training.
    if not torch.is_grad_enabled():
        first_gemm_output = None
        fused_intermediate = None
        intermediate = None
        gate_up_lora_delta = None
        permuted_hidden = None
        lora_delta = None
        gate = None
        up = None
        _verifact_memory_release_counter[0] += 1
'''
  modified=source.replace(anchor,insertion+anchor);module.__dict__['_verifact_memory_release_counter']=[0]
  exec(compile(modified,'verifact103_moe_lifetime_fix','exec'),module.__dict__)
  patched.append((name,module))
  gw.write(a.work/('memory_lifetime_patch_'+str(len(patched))+'.json'),dict(module=name,original_source_sha256=hashlib.sha256(source.encode()).hexdigest(),patched_source_sha256=hashlib.sha256(modified.encode()).hexdigest(),inference_only=True,arithmetic_and_dtype_unchanged=True,all_model_parameters_remain_on_GPU=True))
 assert patched,'No matching MoE backend; do not silently claim the fix applied'
 return model,tok,Fast,torch
def inference(model,tok,Fast,torch,a):
 batch.inference(model,tok,Fast,torch,a)
 counts={name:module.__dict__['_verifact_memory_release_counter'][0] for name,module in patched}
 assert any(counts.values()),'Memory fix was not used'
 gw.write(a.work/'memory_lifetime_patch_used.json',counts)
if __name__=='__main__':gw.load=load;gw.inference=inference;gw.main()
