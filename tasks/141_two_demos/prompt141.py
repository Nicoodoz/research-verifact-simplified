"""Two fixed complete training examples before the unchanged136 target user."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/136_claim_repeat_transfer'))
from prompt136 import messages as original136_messages
EXAMPLE_IDS=('93cd2c13-0d5a-b617-eb23-a479e6549d9b','e96580ee-ad16-3d5a-4b29-3739cd1b46bc')
ANSWERS=('{"verdict":"Supported"}','{"verdict":"Not Supported"}')
_EXAMPLES=None


def validate_examples(examples):
    if tuple(r['id'] for r in examples)!=EXAMPLE_IDS:raise ValueError('Fixed S/NS example order changed')
    if tuple(r['answer'] for r in examples)!=ANSWERS:raise ValueError('Original compact label answers changed')
    if any(not isinstance(r['claim'],str) or not isinstance(r['reference'],str) for r in examples):
        raise ValueError('Complete claim/reference strings required')
    return examples


def configure_examples(examples):
    global _EXAMPLES
    _EXAMPLES=validate_examples(examples)


def messages(row,examples=None):
    examples=validate_examples(examples if examples is not None else _EXAMPLES)
    target=original136_messages(row);result=[target[0]]
    for example in examples:
        result.append(original136_messages(example)[1])
        result.append(dict(role='assistant',content=example['answer']))
    result.append(target[1])
    return result


def prompt_ids(tokenizer,row,examples=None):
    return tokenizer.apply_chat_template(messages(row,examples),tokenize=True,
        add_generation_prompt=True,enable_thinking=False,reasoning_effort='low')
