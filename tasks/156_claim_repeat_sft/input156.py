"""One scientific change: use136 claim repetition for both SFT prefixes and inference."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))
from prompt136 import prompt_ids as original136_prompt_ids

def repeat_prompt_ids(tokenizer,row):
    value=original136_prompt_ids(tokenizer,row)
    if hasattr(value,'get'):value=value['input_ids']
    if value and isinstance(value[0],list):value=value[0]
    if not isinstance(value,list) or not value:raise ValueError('Full136 prefix required')
    return value
