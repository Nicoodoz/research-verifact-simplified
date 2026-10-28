"""No-card verification from copied env; never import Torch or load9B."""
from pathlib import Path
import importlib.metadata as md,json,sys,time
ROOT=Path('/root/verifact_image');BUNDLE=ROOT/'105/bundle';TASK=BUNDLE/'tasks/105_brief_supervision'
assert Path(sys.prefix).resolve()==ROOT/'envs/venv103',sys.prefix
assert not any('/root/autodl-tmp' in str(p) for p in sys.path)
sys.path.insert(0,str(TASK))
import common105 as c
from verify105 import bundle
from data105 import encode,shared
from tokenizer_cpu105 import CPUPinnedTokenizer
bundle(BUNDLE)
versions={}
for name,wanted in c.read(BUNDLE/'frozen/environment_versions.json').items():
    actual=md.version(name);location=str(md.distribution(name).locate_file('').resolve())
    assert actual==wanted and location.startswith(str(ROOT/'envs/venv103')),name
    versions[name]=dict(expected=wanted,actual=actual,location=location)
tok=CPUPinnedTokenizer(ROOT/'models/qwen3.5-9b')
lengths={(r['arm'],r['id']):r for r in c.rows(BUNDLE/'frozen/train_token_lengths.jsonl')}
count=0
for arm in ('label_only','evidence_brief'):
    for row in c.rows(BUNDLE/'data/train'/(arm+'.jsonl')):
        actual=encode(tok,row);wanted=lengths[(arm,row['id'])]
        assert actual['prompt_token_sha256']==wanted['prompt_token_sha256'] and actual['answer_sha256']==wanted['answer_sha256']
        assert actual['verdict_answer_token_indices']==wanted['verdict_answer_token_indices'] and len(actual['input_ids'])==wanted['total_tokens']
        count+=1
evaluation={r['id']:r for r in c.rows(BUNDLE/'frozen/eval_token_lengths.jsonl')}
for row in c.rows(BUNDLE/'data/eval_inputs.jsonl'):
    assert c.digest(c.canonical(shared.prompt_ids(tok,row)))==evaluation[row['id']]['prompt_token_sha256']
assert not any(n=='torch' or n.startswith('torch.') or n=='transformers' or n.startswith('transformers.') for n in sys.modules)
result=dict(epoch=time.time(),status='PASS',actual_prefix=sys.prefix,versions=versions,train_answers_verified=count,
    eval_prompts_verified=len(evaluation),data_disk_not_in_python_path=True,model_loaded=False,torch_or_transformers_imported=False,
    required_base_interpreter='/root/miniconda3/bin/python (already in system image)',
    console_scripts_need_restore_links=True)
c.put(ROOT/'metadata/environment_token_check.json',result);print(c.canonical(result))
