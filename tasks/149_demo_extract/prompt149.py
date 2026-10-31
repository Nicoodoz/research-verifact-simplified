"""141 message order and labels, with fixed extractive demonstration references."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))
from prompt136 import messages as target_messages
EXAMPLES=None

def examples():
    global EXAMPLES
    if EXAMPLES is None:
        EXAMPLES=[json.loads(line) for line in (R/'data/examples.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
        assert [r['id'] for r in EXAMPLES]==['93cd2c13-0d5a-b617-eb23-a479e6549d9b','e96580ee-ad16-3d5a-4b29-3739cd1b46bc']
    return EXAMPLES

def messages(row):
    target=target_messages(row);result=[target[0]]
    for example in examples():
        result.append(target_messages(example)[1]);result.append(dict(role='assistant',content=example['answer']))
    result.append(target[1]);return result

def prompt_ids(tokenizer,row):
    value=tokenizer.apply_chat_template(messages(row),tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
    if hasattr(value,'get'):value=value['input_ids']
    if value and isinstance(value[0],list):value=value[0]
    return value
