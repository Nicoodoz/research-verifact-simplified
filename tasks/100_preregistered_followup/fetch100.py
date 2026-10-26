"""Official model/tokenizer metadata only; no model weights or paid requests."""
import importlib.util,urllib.request
import common100 as c

def get(url,name):
 p=c.PRIVATE/'sources'/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():b=p.read_bytes()
 else:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'VeriFact-100-source-check'}),timeout=120) as r:b=r.read()
  p.write_bytes(b)
 return b,dict(url=url,path=p.relative_to(c.ROOT).as_posix(),sha256=c.sha(p),bytes=len(b))
def main():
 import json
 repo='deepseek-ai/DeepSeek-V4-Flash-0731'
 b,source=get('https://huggingface.co/api/models/'+repo,'HF_metadata.json');meta=json.loads(b);rev=meta['sha'];out=[source]
 for name in ['tokenizer.json','tokenizer_config.json','config.json']:
  _,s=get(f'https://huggingface.co/{repo}/resolve/{rev}/{name}',name);out.append(s)
 for key,url in [('prices','https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices'),('capacity','https://platform.qianwenai.com/docs/developer-guides/getting-started/text-generation-models')]:
  _,s=get(url,key+'.html');out.append(s)
 doc=dict(utc=c.utc(),model='deepseek-v4-flash-0731',tokenizer_repo=repo,revision=rev,files=out,
  prices_CNY_per_million=dict(peak=[3,9,.3],idle=[1.5,4.5,.15]),idle_UTC8='22:00 to next08:00',API_context_tokens=1000000,local_config_context=c.read(c.PRIVATE/'sources/config.json')['max_position_embeddings'],
  no_weights_downloaded=True,no_paid_API=True,tokenizers_in_CPU_environment=importlib.util.find_spec('tokenizers') is not None)
 c.put(c.OUT/'source_registry.json',doc);print(c.canonical({k:v for k,v in doc.items() if k!='files'}))
if __name__=='__main__':main()
