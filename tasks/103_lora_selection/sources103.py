"""Read-only official metadata/tokenizers; no model weights or paid completions."""
import urllib.request,urllib.error,concurrent.futures as cf
import common103 as c
def fetch(url,path):
 path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists():
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'VeriFact103-preparation'}),timeout=90) as r:b=r.read(40_000_001)
  assert len(b)<40_000_001;path.write_bytes(b)
 return {'url':url,'path':path.relative_to(c.ROOT).as_posix(),'sha256':c.sha(path),'bytes':path.stat().st_size}
def model(pair):
 name,repo=pair;folder=c.PRIVATE/'models'/name
 api=fetch('https://huggingface.co/api/models/'+repo,folder/'metadata.json');info=c.read(c.ROOT/api['path']);rev=info['sha'];files={}
 for part in ['config.json','generation_config.json','chat_template.jinja','tokenizer.json','tokenizer_config.json','model.safetensors.index.json','README.md']:
  try:files[part]=fetch(f'https://huggingface.co/{repo}/resolve/{rev}/{part}',folder/part)
  except urllib.error.HTTPError as e:
   if e.code==404 and part=='generation_config.json':files[part]={'absent':True}
   else:raise
 return name,dict(repo=repo,revision=rev,files=files,weight_bytes=c.read(folder/'model.safetensors.index.json')['metadata']['total_size'],api_precision='unknown',api_revision='unknown')
def main():
 with cf.ThreadPoolExecutor(max_workers=5) as pool:models=dict(pool.map(model,c.REPOS.items()))
 c.put(c.OUT/'model_metadata.json',models)
 docs={
 'prices':'https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices',
 'chat':'https://platform.qianwenai.com/docs/api-reference/chat/openai-chat',
 'unsloth_qwen35':'https://unsloth.ai/docs/models/qwen3.5/fine-tune',
 'peft_lora':'https://huggingface.co/docs/peft/en/developer_guides/lora',
 'transformers_pypi':'https://pypi.org/pypi/transformers/json',
 'peft_pypi':'https://pypi.org/pypi/peft/json',
 'torch_pypi':'https://pypi.org/pypi/torch/json',
 'unsloth_pypi':'https://pypi.org/pypi/unsloth/json',
 }
 records=[fetch(url,c.PRIVATE/'sources'/(name+'.txt')) for name,url in docs.items()]
 c.put(c.OUT/'source_manifest.json',dict(utc=c.utc(),docs=records,weight_downloaded=False))
 print(c.canonical({m:{k:v[k] for k in ['revision','weight_bytes']} for m,v in models.items()}))
if __name__=='__main__':main()
