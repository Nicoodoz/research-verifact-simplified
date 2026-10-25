"""Deployment path: claim/reference only; no label, LLM score or cached representation required."""
import os,argparse,time,json
os.environ['HF_HUB_OFFLINE']='1';os.environ['TOKENIZERS_PARALLELISM']='false'
import torch
from transformers import AutoTokenizer,AutoModel
import common092 as c
from cache092 import windows
from model092 import Verifier
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--checkpoint',required=True);parser.add_argument('--input',required=True);parser.add_argument('--output',required=True);args=parser.parse_args();torch.set_num_threads(4)
    cfg=c.read(c.TASK/'config.json');tok=AutoTokenizer.from_pretrained(c.ROOT/'.local_models/032/deberta_v3_nli',local_files_only=True);base=AutoModel.from_pretrained(c.ROOT/'.local_models/032/deberta_v3_nli',local_files_only=True,torch_dtype=torch.float16).cuda().eval()
    net=Verifier(adapt=False).cuda().eval();net.load_state_dict(torch.load(args.checkpoint,map_location='cuda',weights_only=True))
    # The pretrained lower encoder is run online; adapted final block sees exactly its output.
    base.encoder.layer=torch.nn.ModuleList(list(base.encoder.layer)[:-1]);out=[];started=time.time()
    for row in c.lines(args.input):
        ww,_=windows(tok,row['text'],row['reference'],cfg);features=[];t=time.time()
        with torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            for lo in range(0,len(ww),2):
                batch=tok.pad([dict(input_ids=w['input_ids'],attention_mask=[1]*len(w['input_ids'])) for w in ww[lo:lo+2]],return_tensors='pt').to('cuda');h=base(**batch).last_hidden_state;features.append(net.encode(h.float(),batch['attention_mask']))
            logits=net.head(torch.cat(features).float()).float();prob=logits.softmax(-1)
        out.append(dict(id=row.get('proposition_id',row.get('id')),prediction=c.LABELS[int(prob.argmax())],probabilities=prob.cpu().tolist(),seconds=time.time()-t,windows=len(ww)))
    c.jsonl(args.output,out);print('inference',len(out),'seconds',time.time()-started,flush=True)
if __name__=='__main__':main()
