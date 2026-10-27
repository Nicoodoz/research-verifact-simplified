"""Small exact request-length pass so API work need not await whole-training census."""
from tokenizers import Tokenizer
from jinja2.sandbox import ImmutableSandboxedEnvironment
import common103 as c
from prompt103 import messages
def main():
 rows=c.lines(c.PRIVATE/'sample240.jsonl');out=[]
 for m in c.MODELS:
  folder=c.PRIVATE/'models'/m;tok=Tokenizer.from_file(str(folder/'tokenizer.json'));tok.no_truncation();tok.no_padding()
  env=ImmutableSandboxedEnvironment(trim_blocks=True,lstrip_blocks=True)
  template=env.from_string((folder/'chat_template.jinja').read_text(encoding='utf-8'))
  for r in rows:
   d={}
   for mode in ['native','label']:
    text=template.render(messages=messages(r['claim'],r['reference'],mode),add_generation_prompt=True,enable_thinking=mode=='native',reasoning_effort='low')
    d[mode]=len(tok.encode(text,add_special_tokens=False).ids)
   out.append(dict(id=r['id'],model=m,**d))
 c.putl(c.OUT/'api_token_lengths.jsonl',out);print('counted',len(out))
if __name__=='__main__':main()
