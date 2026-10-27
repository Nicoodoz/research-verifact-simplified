"""No correctness access: price, endpoint, token counts and usage-only forecast."""
import urllib.request,urllib.error,json,statistics,sys
import common103 as c
from verifact_research.inference.aliyun import load_config
def main():
 cfg=load_config(c.ROOT/'.env.aliyun');assert cfg.base_url.rstrip('/')==c.ENDPOINT
 try:
  req=urllib.request.Request(c.ENDPOINT+'/models',headers={'Authorization':'Bearer '+cfg.api_key})
  with urllib.request.urlopen(req,timeout=45) as res:data=json.load(res)
  names=sorted(x['id'] for x in data.get('data',[]) if x.get('id') in list(c.MODELS)+['qwen3.5-9b'])
  inventory={'http_status':200,'candidate_ids':names}
 except urllib.error.HTTPError as e:inventory={'http_status':e.code,'candidate_ids':[]}
 prices=(c.PRIVATE/'sources/prices.txt').read_text(encoding='utf-8')
 c.put(c.OUT/'api_readonly_check.json',dict(utc=c.utc(),endpoint=c.ENDPOINT,inventory=inventory,qwen35_9b_price_listed='qwen3.5-9b' in prices,api9b_action='local_only_without_both_explicit_model_and_price',prices=c.PRICES,thinking_budget=4096,qwen38_mapped_effort='low',no_peak_wait=True))
 print(c.canonical(c.read(c.OUT/'api_readonly_check.json')))
if __name__=='__main__':main()
