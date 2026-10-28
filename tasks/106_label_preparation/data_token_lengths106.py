"""Pinned-tokenizer CPU index; no torch import, weights, network, or clinical print."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/104_supervision_evidence'))
from training104 import messages
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
from tokenizer_cpu105 import CPUPinnedTokenizer

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(text):return hashlib.sha256(text.encode('utf-8')).hexdigest()

def main():
    source=ROOT/'.local_models/103_lora_selection/eligible.jsonl'
    folder=ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b'
    metadata=json.loads((ROOT/'outputs/103_lora_selection/model_metadata.json').read_text(encoding='utf-8-sig'))['qwen3.5-9b']
    files={name:sha(folder/name) for name in ('tokenizer.json','tokenizer_config.json','chat_template.jinja')}
    assert all(value==metadata['files'][name]['sha256'] for name,value in files.items())
    allowed=set(json.loads((ROOT/'outputs/103_lora_selection/patient_roles.json').read_text(encoding='utf-8-sig'))['patients']['train'])
    tok=CPUPinnedTokenizer(folder)
    lengths=[]
    with source.open(encoding='utf-8-sig') as handle:
        for line in handle:
            r=json.loads(line)
            if r['role']!='train':continue
            assert r['sid'] in allowed
            prompt=tok.apply_chat_template(messages(r['claim'],r['reference']),tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
            lengths.append(dict(id=r['id'],claim_sha256=digest(r['claim']),reference_sha256=digest(r['reference']),
                claim_tokens=len(tok.encode(r['claim'])),reference_tokens=len(tok.encode(r['reference'])),
                input_tokens=len(prompt),input_token_sha256=digest(json.dumps(prompt,separators=(',',':')))))
    assert len(lengths)==3675 and len({r['id'] for r in lengths})==3675
    import tokenizers,jinja2
    out=ROOT/'.local_models/106_label_preparation/data_token_lengths.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(dict(source_sha256=sha(source),tokenizer_files=files,lengths=lengths,
        environment=dict(python=sys.version,executable=sys.executable,tokenizers=tokenizers.__version__,jinja2=jinja2.__version__),
        torch_imported='torch' in sys.modules,model_weights_loaded=False),ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8'))
    print(json.dumps(dict(N=len(lengths),sum_input_tokens=sum(r['input_tokens'] for r in lengths),max_input_tokens=max(r['input_tokens'] for r in lengths),tokenizers=tokenizers.__version__,torch_imported='torch' in sys.modules)))

if __name__=='__main__':main()
