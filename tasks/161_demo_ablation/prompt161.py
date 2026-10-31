"""Fixed leave-one-label-out subsets of the exact152 demonstrations."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))
from prompt136 import messages as target_messages
EXAMPLES=None
ALLOWED=[['e96580ee-ad16-3d5a-4b29-3739cd1b46bc','eec5864a-fa13-48a6-37db-ebfbc0fb3aa8'],['93cd2c13-0d5a-b617-eb23-a479e6549d9b','eec5864a-fa13-48a6-37db-ebfbc0fb3aa8']]

def prompt_ids(tokenizer,row):
    global EXAMPLES
    if EXAMPLES is None:
        EXAMPLES=[json.loads(s) for s in (R/'data/examples.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
        assert [r['id'] for r in EXAMPLES] in ALLOWED
    target=target_messages(row);message=[target[0]]
    for example in EXAMPLES:message.extend([target_messages(example)[1],dict(role='assistant',content=example['answer'])])
    message.append(target[1]);value=tokenizer.apply_chat_template(message,tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
    if hasattr(value,'get'):value=value['input_ids']
    if value and isinstance(value[0],list):value=value[0]
    return value
