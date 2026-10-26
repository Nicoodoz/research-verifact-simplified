"""Official public documentation and small model metadata only; no weights/GPUs."""
import concurrent.futures as cf
import urllib.request
import common099 as c

DOCS={
 'current_prices':'https://platform.qianwenai.com/docs/developer-guides/getting-started/model-prices',
 'chat_parameters':'https://platform.qianwenai.com/docs/api-reference/chat/openai-chat',
 'current_flash':'https://platform.qianwenai.com/docs/developer-guides/getting-started/latest-model',
 'vllm_qwen35':'https://docs.vllm.ai/projects/recipes/en/latest/Qwen/Qwen3.5.html',
 'vllm_quantization':'https://docs.vllm.ai/en/latest/features/quantization/',
}

def fetch(name,url):
    req=urllib.request.Request(url,headers={'User-Agent':'Research-VeriFact099-metadata-audit'})
    with urllib.request.urlopen(req,timeout=45) as r:
        b=r.read(3_000_001);assert len(b)<=3_000_000
        final=r.url
    p=c.PRIVATE/'sources'/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():assert p.read_bytes()==b
    else:p.write_bytes(b)
    return dict(name=name,url=url,resolved_url=final,sha256=c.sha(p),bytes=len(b),path=p.relative_to(c.ROOT).as_posix())

def main():
    manifest=[];metadata={}
    for model,repo in c.REPOS.items():
        name=model.replace('.','_')
        info=fetch(name+'_api','https://huggingface.co/api/models/'+repo)
        manifest.append(info);raw=c.read(c.ROOT/info['path']);revision=raw['sha']
        parts={}
        urls={part:f'https://huggingface.co/{repo}/resolve/{revision}/{part}' for part in ['README.md','config.json','generation_config.json','chat_template.jinja','model.safetensors.index.json']}
        with cf.ThreadPoolExecutor(max_workers=4) as pool:
            fut={pool.submit(fetch,name+'_'+part.replace('.','_'),url):part for part,url in urls.items()}
            for f,part in fut.items():
                try:r=f.result();manifest.append(r);parts[part]=r
                except Exception as e:parts[part]=dict(error_type=type(e).__name__)
        config=c.read(c.ROOT/parts['config.json']['path']);tc=config.get('text_config',config)
        index=c.read(c.ROOT/parts['model.safetensors.index.json']['path']) if 'path' in parts['model.safetensors.index.json'] else {}
        safetensors=raw.get('safetensors',{})
        metadata[model]=dict(repo=repo,revision=revision,license=raw.get('cardData',{}).get('license'),
          safetensors=safetensors,weight_bytes=index.get('metadata',{}).get('total_size'),
          architecture=config.get('architectures'),dtype=tc.get('dtype',tc.get('torch_dtype')),hidden_layers=tc.get('num_hidden_layers'),
          full_attention_layers=sum(x=='full_attention' for x in tc.get('layer_types',[])),KV_heads=tc.get('num_key_value_heads'),head_dim=tc.get('head_dim'),
          context=tc.get('max_position_embeddings'),num_experts=tc.get('num_experts'),parts=parts,
          API_weight_revision_verified=False,API_precision_verified=False,
          single_A800_high_fidelity_candidate=model!='qwen3.8-flash')
    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        futures={pool.submit(fetch,name,url):name for name,url in DOCS.items()}
        for f,name in futures.items():
            try:manifest.append(f.result())
            except Exception as e:manifest.append(dict(name=name,url=DOCS[name],error_type=type(e).__name__))
    c.put(c.OUT/'official_source_manifest.json',dict(utc=c.utc(),sources=manifest,weights_downloaded=False,paid_API_calls=0))
    c.put(c.OUT/'model_metadata.json',metadata)
    print(c.canonical({m:{k:v[k] for k in ['repo','revision','dtype','weight_bytes','single_A800_high_fidelity_candidate']} for m,v in metadata.items()}))

if __name__=='__main__':main()
