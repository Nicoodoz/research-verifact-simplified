"""Native generation-order intervention; no prefilled clinical facts or labels."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/134_author_baselines'))
from prompt134 import messages as original_messages

VARIANT='reason_first'
RESPONSE_PREFIX='{"reason": "'
OLD='5. Format your response as a JSON object with the keys "verdict" and "reason". Return only JSON.'
NEW='5. Format your response as a JSON object with the keys "reason" and "verdict", in that order. Return only JSON.'

def configure(variant):
    global VARIANT,RESPONSE_PREFIX
    if variant not in ('reason_first','verdict_prefix'):raise ValueError(variant)
    VARIANT=variant
    RESPONSE_PREFIX='{"reason": "' if variant=='reason_first' else '{"verdict": "'
    return RESPONSE_PREFIX

def messages(row):
    value=original_messages(row)
    if VARIANT=='reason_first':
        assert value[1]['content'].count(OLD)==1
        value[1]['content']=value[1]['content'].replace(OLD,NEW)
    return value

def unprefilled_ids(tokenizer,row):
    return tokenizer.apply_chat_template(messages(row),tokenize=True,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')

def prompt_ids(tokenizer,row):
    text=tokenizer.apply_chat_template(messages(row),tokenize=False,add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
    return tokenizer.encode(text+RESPONSE_PREFIX,add_special_tokens=False)
