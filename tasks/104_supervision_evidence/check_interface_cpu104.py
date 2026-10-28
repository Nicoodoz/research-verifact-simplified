"""Actual pinned 9B tokenizer smoke check using only synthetic engineering text.

This is not a clinical data-construction or model-performance experiment.
"""
from pathlib import Path
import tempfile
import json
import platform

import common104 as c
import build104 as b
import training104 as t
from tokenize104 import LocalTokenizer, file_sha
from test_build104 import case, review


def main():
    folder=c.ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b'
    meta=c.read(c.ROOT/'outputs/103_lora_selection/model_metadata.json')['qwen3.5-9b']
    for name in ('tokenizer.json','tokenizer_config.json','chat_template.jinja'):
        assert file_sha(folder/name)==meta['files'][name]['sha256']
    tokenizer=LocalTokenizer(folder)
    import tokenizers, jinja2
    reference='1. Date: TEST, Note ID: fixture1 | Text: Alpha event occurred.\n2. Date: TEST | Text: Alpha event occurred.\n'
    first=case(1,reference);first_review=review(first)
    first_meta=dict(evidence_spans=b.evidence_spans(reference,first_review['evidence_quotes'])[0],full_reference_read=True)
    second=case(2,'1. Date: TEST | Text: A different synthetic event is recorded.\n')
    second_review=review(second)
    second_review.update(independent_verdict='Not Addressed',evidence_quotes=[],na_anchor='none',relation='The supplied source discusses a different synthetic event and does not address the asserted event. This is an engineering fixture, not a clinical annotation.')
    pairs=[b.pair_rows(first,first_review,'Supported',first_meta),b.pair_rows(second,second_review,'Not Addressed',dict(evidence_spans=[],no_anchor_na=True,full_reference_read=True))]
    with tempfile.TemporaryDirectory(prefix='verifact104_cpu_interface_') as temp:
        pair_dir=Path(temp)/'candidate_paired';pair_dir.mkdir()
        c.putl(pair_dir/'label_only.jsonl',[x[0] for x in pairs])
        c.putl(pair_dir/'evidence_brief.jsonl',[x[1] for x in pairs])
        labels=t.load_rows(pair_dir/'label_only.jsonl');briefs=t.load_rows(pair_dir/'evidence_brief.jsonl')
        checked=t.validate_pairs(labels,briefs,{'synthetic_patient'},{'excluded_synthetic_patient'})
        lengths=[]
        for label,brief in zip(labels,briefs):
            assert t.prompt_ids(tokenizer,label)==t.prompt_ids(tokenizer,brief)
            encoded=[t.encode_lists(tokenizer,row) for row in (label,brief)]
            for row,(ids,loss,supervised) in zip((label,brief),encoded):
                assert all(value==-100 for value in loss[:-supervised])
                assert loss[-supervised:]==ids[-supervised:]
                assert tokenizer.decode(loss[-supervised:-1],skip_special_tokens=False)==row['answer']
                assert loss[-1]==tokenizer.convert_tokens_to_ids('<|im_end|>')
                payload=row['messages'][1]['content'].split('## Input JSON:\n',1)[1]
                assert set(json.loads(payload))=={'text','reference'}
            batch=t.pad_batch(encoded,tokenizer.convert_tokens_to_ids('<|endoftext|>'))
            assert all(target==-100 for mask,targets in zip(batch['attention_mask'],batch['labels']) for active,target in zip(mask,targets) if not active)
            lengths.append(dict(input_tokens=len(t.prompt_ids(tokenizer,label)),label_supervised_tokens=encoded[0][2],brief_supervised_tokens=encoded[1][2]))
    result=dict(status='PASS',scope='Synthetic builder-to-loader-to-actual-pinned-tokenizer engineering check only',
                actual_9B_tokenizer=True,revision=meta['revision'],pairs=len(pairs),checks=checked,
                all_occurrences_quote_metadata=True,answer_string_and_answer_text_equal=True,
                prompt_and_padding_loss_masked=True,whole_answer_and_EOS_supervised=True,
                shared_prompt_contains_only_claim_reference_payload=True,
                model_weights_loaded=False,GPU_used=False,new_API_calls=0,
                real_blind_reviews_read=False,GT_join_on_real_data=False,
                tokenizer_environment=dict(python=platform.python_version(),tokenizers=tokenizers.__version__,jinja2=jinja2.__version__,existing_environment='tokenizer-only; no install or upgrade'),
                synthetic_lengths=lengths,
                files={p.name:c.sha(p) for p in [Path(__file__),c.TASK/'build104.py',c.TASK/'training104.py',c.TASK/'tokenize104.py']})
    c.put(c.OUT/'interface_cpu_selfcheck.json',result)
    print(c.canonical(result))


if __name__=='__main__':main()
