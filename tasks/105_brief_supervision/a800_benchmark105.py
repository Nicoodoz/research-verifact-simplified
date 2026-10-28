"""Resource-only A800 measurements: no optimizer step or scored predictions."""
from pathlib import Path
import sys,time,types
R=Path('/root/autodl-tmp/verifact105');B=R/'bundle';sys.path.insert(0,str(B/'tasks/105_brief_supervision'))
import common105 as c
import worker105 as w
import budget105 as budget
a=types.SimpleNamespace(bundle=B,work=R/'results',model_dir=Path('/root/verifact_image/models/qwen3.5-9b'),ledger=R/'budget/ledger.json',mode='resource_benchmark',arm='base_judge')
config=c.read(B/'frozen/config.json');model,tok,Fast,torch=w.load(a,config);model=w.adapt(model,Fast,config,a.work/'gate')
from loss105 import backbone_loss
rows=c.rows(B/'data/train/evidence_brief.jsonl');by={r['id']:r for r in rows};lengths=sorted([r for r in c.rows(B/'frozen/train_token_lengths.jsonl') if r['arm']=='evidence_brief'],key=lambda r:r['total_tokens'])
measure=[]
for entry in [lengths[len(lengths)//2],lengths[-1]]:
 budget.require(a.ledger,120,watchdog=True);row=by[entry['id']];batch,encoded=w.tensor_batch(tok,row,torch);torch.cuda.synchronize();begin=time.perf_counter();model.zero_grad(set_to_none=True);torch.cuda.reset_peak_memory_stats()
 with torch.autocast('cuda',dtype=torch.bfloat16):loss,info=backbone_loss(model,batch,16)
 loss.backward();torch.cuda.synchronize();seconds=time.perf_counter()-begin
 assert bool(torch.isfinite(loss));assert all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None)
 measure.append(dict(id=row['id'],tokens=len(encoded['input_ids']),seconds=seconds,peak_bytes=torch.cuda.max_memory_allocated()));del loss,batch
model.zero_grad(set_to_none=True);torch.cuda.empty_cache();Fast.for_inference(model);model.eval()
ev={r['id']:r for r in c.rows(B/'data/eval_inputs.jsonl')};batches=[b for b in c.read(B/'frozen/eval_batches.json')['batches'] if len(b['ids'])==8];longest=max(batches,key=lambda b:b['max_input_tokens']);seq=[w.shared.prompt_ids(tok,ev[i]) for i in longest['ids']];maximum=max(map(len,seq));pad=tok.pad_token_id
ids=torch.tensor([[pad]*(maximum-len(s))+s for s in seq],device='cuda');mask=torch.tensor([[0]*(maximum-len(s))+[1]*len(s) for s in seq],device='cuda')
decode=[]
for length in [4,128]:
 budget.require(a.ledger,120,watchdog=True);torch.cuda.synchronize();begin=time.perf_counter();torch.cuda.reset_peak_memory_stats()
 with torch.inference_mode():generated=model.generate(input_ids=ids,attention_mask=mask,do_sample=False,num_beams=1,num_return_sequences=1,min_new_tokens=length,max_new_tokens=length,use_cache=True,pad_token_id=pad)
 torch.cuda.synchronize();decode.append(dict(batch_size=8,forced_tokens_per_sequence=length,seconds=time.perf_counter()-begin,peak_bytes=torch.cuda.max_memory_allocated()));del generated
c.put(R/'a800_benchmark.json',dict(training=measure,decode=decode,optimizer_steps=0,scored_predictions=0,answers_decoded_or_inspected=False,formal_data_settings_changed=False,full384_not_run=True))
print(c.canonical(dict(status='resource_measurements_complete',training=measure,decode=decode)))
