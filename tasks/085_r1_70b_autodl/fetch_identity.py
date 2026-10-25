"""Public metadata only; no weights or paid inference. Pin exact upstream identities."""
import urllib.request,time
from common import *
def fetch(url):
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'research-verifact-085-metadata'}),timeout=45) as r:
                b=r.read(4_000_001);assert len(b)<=4_000_000,'metadata bound';return b
        except Exception:
            if i==2:raise
            time.sleep(2**i)
def main():
    OUT.mkdir(parents=True,exist_ok=True);src=OUT/'public_sources';result={}
    for name,repo,rev in [('model',MODEL,'main'),('tokenizer',TOKENIZER,read(OLD/'tokenizer_source.json')['revision'])]:
        url=f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true';raw=fetch(url);info=json.loads(raw);commit=info['sha'];assert len(commit)==40
        write(src/f'{name}_model_info.json',raw)
        files={}
        for item in info['siblings']:
            n=item['rfilename'];lfs=item.get('lfs') or {}
            files[n]=dict(size=item.get('size'),git_blob=item.get('blobId'),sha256=lfs.get('sha256'))
        small={}
        for n in ('config.json','generation_config.json','tokenizer_config.json'):
            b=fetch(f'https://huggingface.co/{repo}/resolve/{commit}/{n}');write(src/f'{name}_{n}',b);small[n]=dict(sha256=digest(b),content=json.loads(b))
        result[name]=dict(repo=repo,revision=commit,files=files,metadata=small,api_url=url)
    old=read(OLD/'tokenizer_source.json');assert result['tokenizer']['revision']==old['revision']
    for n in ('config.json','generation_config.json','tokenizer_config.json'):assert result['tokenizer']['metadata'][n]['sha256']==old['files'][n]['sha256']
    upstream='f115d36cb65fa2073fce0a10df56bb37f4cbcd50'
    for n,path in [('verifact_docker_compose.yml','docker-compose.yml'),('verifact_r1_70b.env','configs/inference/r1-70b.env')]:
        b=fetch(f'https://raw.githubusercontent.com/philipchung/verifact/{upstream}/{path}');write(src/n,b)
    for n,path in [('vllm_cli_args.py','vllm/entrypoints/openai/cli_args.py'),('vllm_engine_args.py','vllm/engine/arg_utils.py')]:
        write(src/n,fetch('https://raw.githubusercontent.com/vllm-project/vllm/v0.9.2/'+path))
    result.update(created_utc=now(),verifact_source_revision=upstream,weight_downloaded=False,inference_calls=0,
        original_checkpoint_revision_known=False,original_checkpoint_note='Upstream serving config names repository but does not pin HF revision; repository identity is established, original historical loaded bytes are not established.')
    put(OUT/'identity_target.json',result)
    # Portable metadata lock for remote validation, never model weights.
    put(TASK/'identity_lock.json',dict(model=result['model'],tokenizer=result['tokenizer'],official_tokenizer_files=old['files'],
        chat_template_sha256=sha(OLD/'chat_template.jinja'),vllm_version='0.9.2',original_checkpoint_revision_known=False))
    print(canonical(dict(model_revision=result['model']['revision'],tokenizer_revision=result['tokenizer']['revision'],quantization=result['model']['metadata']['config.json']['content'].get('quantization_config'),
        weight_bytes=sum(x['size'] or 0 for n,x in result['model']['files'].items() if n.endswith('.safetensors')))))
if __name__=='__main__':main()
