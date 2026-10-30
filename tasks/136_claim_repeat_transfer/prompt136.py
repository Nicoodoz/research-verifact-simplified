"""Exact116 claim repetition transferred to120; no extra evidence or GT."""
from pathlib import Path
import json,sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/104_supervision_evidence'))
from training104 import messages as original_messages
RESPONSE_PREFIX=''
def configure(variant):
    assert variant=='claim_repeat'
    return RESPONSE_PREFIX
def messages(row):
    result=original_messages(row['claim'],row['reference'])
    result[-1]['content']+='\n\n## Text being verified (repeated; not reference evidence):\n'+json.dumps(row['claim'],ensure_ascii=False)+'\nApply the same three verdict definitions to this text, using only the reference above.'
    return result
def prompt_ids(tokenizer,row):
    return tokenizer.apply_chat_template(messages(row),tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
unprefilled_ids=prompt_ids
