"""Loopback OpenAI-compatible transport. No SSH, AWS, AutoDL API or credentials."""
import urllib.request,urllib.error,urllib.parse,time
from common import *
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise ValueError('Endpoint redirects disabled')
def base_url(value=None):
    value=value or os.getenv('R1_BASE_URL')
    if not value:raise RuntimeError('R1_BASE_URL not configured; establish user-managed SSH tunnel first')
    p=urllib.parse.urlsplit(value)
    if p.scheme!='http' or p.hostname not in ('127.0.0.1','localhost','::1') or p.username or p.password or p.query or p.fragment or p.path.rstrip('/')!='/v1':
        raise ValueError('Only credential-free loopback http://.../v1 accepted')
    return value.rstrip('/')
class Transport:
    def __init__(self,url=None,timeout=900):
        if not 0<timeout<=1800:raise ValueError('Transport timeout must be in (0,1800] seconds')
        self.url=base_url(url);self.timeout=timeout;self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def request(self,path,body=None):
        headers={'Authorization':'Bearer EMPTY','Content-Type':'application/json'}
        req=urllib.request.Request(self.url+path,data=canonical(body).encode() if body is not None else None,headers=headers)
        start=now();t=time.monotonic()
        try:
            with self.opener.open(req,timeout=self.timeout) as r:raw=r.read();status=r.status
            out=dict(http_status=status,raw=raw,error_type=None,outcome_unknown=False)
        except urllib.error.HTTPError as e:out=dict(http_status=e.code,raw=e.read(),error_type='HTTPError',outcome_unknown=False)
        except (OSError,ValueError) as e:out=dict(http_status=0,raw=b'',error_type=type(e).__name__,outcome_unknown=body is not None)
        return dict(out,started_utc=start,ended_utc=now(),elapsed_seconds=time.monotonic()-t)
def validate_manifest(manifest,observation,lock):
    if manifest['status']!='VERIFIED_FILES_BEFORE_SERVER_START':raise ValueError('Manifest not verified')
    if observation['status']!='SERVICE_READY_OBSERVED':raise ValueError('Missing live service observation')
    for k in ('model','tokenizer'):
        if manifest[k]['repo']!=lock[k]['repo'] or manifest[k]['resolved_revision']!=lock[k]['revision']:raise ValueError(f'{k} differs from target; STOP for user decision')
        expected=lock[k]['files'] if k=='model' else {n:dict(sha256=v['sha256'],size=v['bytes']) for n,v in lock['official_tokenizer_files'].items()}
        actual={x['name']:x for x in manifest[k]['files']}
        required={n for n in expected if n.endswith('.safetensors') or n.endswith('.index.json') or n in ('config.json','generation_config.json')} if k=='model' else set(expected)
        if set(actual)!=required:raise ValueError('Identity file set incomplete')
        for n in required:
            exp=expected[n];alg='sha256' if exp.get('sha256') else 'git_blob'
            if actual[n]['algorithm']!=alg or actual[n]['actual']!=exp[alg] or actual[n]['expected']!=exp[alg]:raise ValueError('Identity content fingerprint mismatch')
    if manifest['versions']['vllm']!='0.9.2' or observation['version'].get('version')!='0.9.2':raise ValueError('vLLM version differs')
    if manifest['model']['quantization']!=lock['model']['metadata']['config.json']['content']['quantization_config']:raise ValueError('Quantization differs')
    if manifest['tokenizer']['chat_template_sha256']!=lock['chat_template_sha256']:raise ValueError('Chat template differs')
    if manifest['environment'].get('VLLM_USE_V1')!='1':raise ValueError('V1 not recorded')
    from remote_server import command
    # Python executable is remote; all remaining argv must match immutable command builder.
    expected=command(manifest['model']['local_path'],manifest['tokenizer']['local_path'],lock,int(manifest['server_command'][manifest['server_command'].index('--port')+1]))
    if manifest['server_command'][1:]!=expected[1:] or observation['actual_process_command']!=manifest['server_command']:raise ValueError('Server command differs')
    if not manifest.get('gpu'):raise ValueError('GPU identity missing')
    ids={x['id'] for x in observation['models']['data']}
    if MODEL not in ids:raise ValueError('Served name differs; name alone never verifies weights')
    card=next(x for x in observation['models']['data'] if x['id']==MODEL)
    if card.get('max_model_len')!=20000:raise ValueError('Live model card does not confirm max_model_len20000')
    return True
