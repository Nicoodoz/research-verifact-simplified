"""Download only public model assets; no clinical data or credentials are read."""
import os,json,hashlib,datetime
from pathlib import Path
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
os.environ['HF_HUB_DISABLE_XET']='1'
from huggingface_hub import snapshot_download
ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'.local_models/032/deberta_v3_nli'
REPO='MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli'
REV='b3546ea6b0346eb6f8d5d68b13c7dc6d0376b3d7'
FILES=['README.md','config.json','model.safetensors','tokenizer.json','tokenizer_config.json','special_tokens_map.json','added_tokens.json','spm.model']
if __name__=='__main__':
    print('Downloading public NLI weights',REPO,REV,flush=True)
    snapshot_download(repo_id=REPO,revision=REV,local_dir=str(DEST),allow_patterns=FILES,token=False,max_workers=2)
    hashes={}
    for name in FILES:
        path=DEST/name
        if not path.exists():raise FileNotFoundError(path)
        h=hashlib.sha256()
        with path.open('rb') as f:
            for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
        hashes[name]={'sha256':h.hexdigest(),'bytes':path.stat().st_size}
    out=ROOT/'outputs/032_evidence_relation_correction';out.mkdir(parents=True,exist_ok=True)
    manifest={'repository':REPO,'revision':REV,'downloaded_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'local_path':str(DEST),'files':hashes,'clinical_data_uploaded':False}
    (out/'model_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Download and hashes complete',flush=True)
