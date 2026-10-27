"""Run in existing tokenizer-only environment; exact official templates, no truncation."""
import sys,json
from pathlib import Path
from tokenizers import Tokenizer
from jinja2.sandbox import ImmutableSandboxedEnvironment
import common103 as c
from prompt103 import messages
def fail(s):raise ValueError(s)
def main():
 models=c.read(c.OUT/'model_metadata.json');rows=c.lines(c.PRIVATE/'eligible.jsonl');sample={r['id']:r for r in c.lines(c.PRIVATE/'sample240.jsonl')};train={r['id'] for r in c.lines(c.PRIVATE/'train512.jsonl')}
 result=[]
 for m in models:
  folder=c.PRIVATE/'models'/m;tok=Tokenizer.from_file(str(folder/'tokenizer.json'));tok.no_truncation();tok.no_padding()
  env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True);env.globals['raise_exception']=fail
  template=env.from_string((folder/'chat_template.jinja').read_text(encoding='utf-8'))
  for i,r in enumerate(rows):
   vals={}
   for mode in ['native','label']:
    text=template.render(messages=messages(r['claim'],r['reference'],mode),add_generation_prompt=True,enable_thinking=mode=='native',reasoning_effort='low')
    vals[mode]=len(tok.encode(text,add_special_tokens=False).ids)
   result.append(dict(id=r['id'],sid=r['sid'],role=r['role'],model=m,train512=r['id'] in train,api240=r['id'] in sample,**vals))
  print(m,'counted',len(rows),flush=True)
 c.putl(c.OUT/'token_lengths.jsonl',result)
if __name__=='__main__':main()
