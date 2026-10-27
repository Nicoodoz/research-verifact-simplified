"""Actual official tokenizer/template masks, including longest training reference."""
from tokenizers import Tokenizer
from jinja2.sandbox import ImmutableSandboxedEnvironment
import common103 as c
from gpu_worker103 import encode_lists,prompt_ids
from prompt103 import messages
class OfficialTokenizer:
 def __init__(self,folder):
  self.tok=Tokenizer.from_file(str(folder/'tokenizer.json'));self.tok.no_truncation();self.tok.no_padding();self.template=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True).from_string((folder/'chat_template.jinja').read_text(encoding='utf-8'))
 def apply_chat_template(self,msgs,**kw):return self.encode(self.template.render(messages=msgs,**kw))
 def encode(self,s,**kw):return self.tok.encode(s,add_special_tokens=False).ids
 def decode(self,ids):return self.tok.decode(ids,skip_special_tokens=False)
 def convert_tokens_to_ids(self,s):return self.tok.token_to_id(s)
def main():
 train=c.lines(c.PRIVATE/'train512.jsonl');lengths=c.lines(c.OUT/'token_lengths.jsonl');checks=[]
 for m in c.REPOS:
  tok=OfficialTokenizer(c.PRIVATE/'models'/m);lm={r['id']:r['label'] for r in lengths if r['model']==m};cases=train[:4]+sorted(train,key=lambda r:lm[r['id']],reverse=True)[:3]
  for r in cases:
   ids,labels,n=encode_lists(tok,r);prefix=prompt_ids(tok,r,'label');assert len(prefix)==lm[r['id']];assert ids[:len(prefix)]==prefix;assert labels[:len(prefix)]==[-100]*len(prefix);assert labels[len(prefix):]==ids[len(prefix):];assert labels[-1]==tok.convert_tokens_to_ids('<|im_end|>')
   checks.append(dict(model=m,id=r['id'],prompt_tokens=len(prefix),supervised_tokens=n,all_prompt_masked=True,full_reference=True))
 c.put(c.OUT/'token_mask_selfcheck.json',dict(status='PASS',checks=checks,GPU_executed=False,real_official_tokenizers=True));print('PASS',len(checks))
if __name__=='__main__':main()
