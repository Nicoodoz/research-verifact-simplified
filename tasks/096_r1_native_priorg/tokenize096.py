"""Local085 tokenizer only. No model weights, downloads or endpoint access."""
import os,statistics,socket
from unittest.mock import patch
os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
import common096 as c
def main():
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(c.TOKENIZER,local_files_only=True,trust_remote_code=False,use_fast=True)
    jobs=c.lines(c.PRIVATE/'jobs.jsonl')+[c.read(c.PRIVATE/'fictional_job.json')];rr=[]
    for j in jobs:
        n=len(tokenizer.apply_chat_template(j['body']['messages'],tokenize=True,add_generation_prompt=True,truncation=False));assert n+8192<=20000
        rr.append(dict(id=j['id'],stage=j['stage'],request_id=j['request_id'],input_tokens=n,max_tokens=8192,total_reserved_context=n+8192,body_sha256=j['body_sha256']))
    c.putl(c.OUT/'local_token_lengths.jsonl',rr)
    cal=sorted([r for r in rr if r['stage']=='calibration'],key=lambda r:(r['input_tokens'],r['id']));technical=[cal[0],cal[len(cal)//2],cal[-1]]
    assert len({r['request_id'] for r in technical})==3
    c.put(c.OUT/'technical_preflight_plan.json',dict(fictional_request_id=rr[-1]['request_id'],calibration_request_ids=[r['request_id'] for r in technical],selection='short/median/long calibration input; not evaluation; first HTTP200 reused for calibration',new_extra_clinical_calls=0,additional_fictional_calls=1,GT_read=False,all_planned_lengths_fit=True))
    c.put(c.OUT/'tokenizer_manifest.json',dict(source='existing local085 Valdemardi files; remote identity NOT verified',expected_model=c.MODEL,known_HF_revision='ebfea7be35ca86beee303282386399416205c306',ModelScope_revision=None,files={n:c.sha(c.TOKENIZER/n) for n in ['config.json','generation_config.json','tokenizer.json','tokenizer_config.json']},chat_template_sha256=c.key('',tokenizer.chat_template),max_input=max(r['input_tokens'] for r in rr),median_input=statistics.median(r['input_tokens'] for r in rr),max_total_context=max(r['total_reserved_context'] for r in rr),network_calls=0))
    print('LOCAL_CONTEXT_PASS',len(rr),'max input',max(r['input_tokens'] for r in rr),'max total',max(r['total_reserved_context'] for r in rr))
if __name__=='__main__':
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Offline tokenizer forbids network')):main()
