"""Repeat the exact complete104 user message; no new evidence or label input."""
from pathlib import Path
import sys
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / 'tasks/104_supervision_evidence'))
from training104 import messages as original_messages


def messages(row):
    value = original_messages(row['claim'], row['reference'])
    content = value[-1]['content']
    value[-1]['content'] = content + '\n\n' + content
    return value


def prompt_ids(tokenizer, row):
    return tokenizer.apply_chat_template(messages(row), tokenize=True,
        add_generation_prompt=True, enable_thinking=False, reasoning_effort='low')


def rope_signature(config):
    text = config.get('text_config', config)
    return {k: text.get(k) for k in ('max_position_embeddings', 'rope_parameters', 'rope_scaling', 'rope_theta')}


def assert_unchanged_rope(source, loaded, capacity):
    expected, actual = rope_signature(source), rope_signature(loaded)
    native_max=expected['max_position_embeddings'];loaded_max=actual['max_position_embeddings']
    expected_rope={k:v for k,v in expected.items() if k!='max_position_embeddings'}
    actual_rope={k:v for k,v in actual.items() if k!='max_position_embeddings'}
    #Unsloth may lower allocation metadata to the requested capacity. With
    #unchanged default RoPE this does not change the original frequency base.
    if expected_rope!=actual_rope or not capacity<=loaded_max<=native_max:
        raise RuntimeError('RoPE parameters changed or allocation exceeds native capacity')
    if loaded_max!=native_max and expected.get('rope_parameters',{}).get('rope_type')!='default':
        raise RuntimeError('Nondefault RoPE requires separate review of context metadata')
    return dict(source_signature=expected,loaded_signature=actual,capacity=capacity,
                allocation_metadata_only_change=loaded_max!=native_max)
