"""One post109 training-set prediction and32 paired true-label losses; no training."""
from pathlib import Path
import argparse,sys,time
from runtime110 import c,load,activate,predict,budget,progress
def main():
    p=argparse.ArgumentParser();
    for name in ['old','model','work','session']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True);model,tok,Fast,torch=load(a)
    from peft import PeftModel
    from data105 import encode
    from loss105 import segmented_hidden_loss
    train=c.rows(a.old/'results/train.jsonl');selected=c.rows(a.old/'results/selected_manifest.jsonl');meta={r['id']:r for r in selected};rows={r['id']:r for r in train}
    if len(rows)!=192 or [r['id'] for r in train]!=[r['id'] for r in selected]:raise ValueError('Actual109 training192 required')
    source=a.old/'results/train/checkpoint_a';sha=c.sha(source/'adapter_model.safetensors')
    if sha!='e3c83143648a2f64ccd60f5b68e1b94bec5e0279c75a3be43c2872ba6ee0b9e8':raise ValueError('Wrong final109 adapter')
    model=PeftModel.from_pretrained(model,source,adapter_name='update109',is_trainable=False);Fast.for_inference(model);activate(model,'update109')
    ids=sorted(rows,key=lambda i:(meta[i]['input_tokens'],i));batches=[dict(batch=n,ids=[i]) for n,i in enumerate(ids)]
    predict(a,model,tok,torch,rows,batches,'train192',dict(source='109_final',adapter_sha256=sha))
    na=[r['id'] for r in selected if r['role']=='retention' and r['GT']=='Not Addressed']
    if len(na)!=32:raise ValueError('Fixed32 actual NA retention required')
    model.load_adapter(a.old/'bundle/source107/checkpoint_a',adapter_name='anchor107',is_trainable=False)
    for arm in ['anchor107','update109']:
        activate(model,arm);results=[];progress(a.work,'NA32_true_label_loss',arm=arm,completed=0,total=32)
        base=model.get_base_model()
        for n,i in enumerate(na):
            budget(a.session);encoded=encode(tok,rows[i]);x=torch.tensor([encoded['input_ids']],device='cuda');groups=torch.tensor([encoded['groups']],device='cuda');mask=torch.ones_like(x)
            with torch.inference_mode(),torch.autocast('cuda',dtype=torch.bfloat16):
                out=base.model(input_ids=x,attention_mask=mask,use_cache=False,return_dict=True);hidden=out.last_hidden_state
                total,info=segmented_hidden_loss(hidden,base.lm_head,x,groups,16,False)
                value_groups=torch.where(groups==1,groups,0);label,_=segmented_hidden_loss(hidden,base.lm_head,x,value_groups,16,False)
            results.append(dict(id=i,GT='Not Addressed',arm=arm,verdict_token_mean_CE=float(label),original_segmented_loss=float(total),**info))
            del out,hidden,x,groups,mask,total,label;progress(a.work,'NA32_true_label_loss',arm=arm,completed=n+1,total=32)
        c.putl(a.work/f'NA32_loss_{arm}.jsonl',results)
    c.put(a.work/'DIAGNOSTIC_GPU_DONE.json',dict(train192=True,NA32_loss_both=True,no_optimizer_created=True,no_training=True))
if __name__=='__main__':main()
