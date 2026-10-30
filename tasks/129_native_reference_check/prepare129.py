"""CPU-only preparation of a fixed160 empty-reference intervention."""
from pathlib import Path
import argparse
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tasks/105_brief_supervision'))
import common105 as common
from data105 import shared
from tokenizer_cpu105 import CPUPinnedTokenizer


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,default=ROOT/'.local_models/129_native_reference_check')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    frozen=common.read(ROOT/'.local_models/117_verdict_probe/data_selection.json')
    selected=frozen['screen_ids'] if isinstance(frozen,dict) else frozen
    inputs={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/inputs_selection1817.jsonl')}
    keys={r['id']:r for r in common.rows(ROOT/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
    if len(selected)!=len(set(selected)) or len(selected)!=160:
        raise ValueError('Only the existing fixed160 is allowed')
    tokenizer=CPUPinnedTokenizer(ROOT/'.local_models/103_lora_selection/models/qwen3.5-9b')
    out=[];links=[]
    for identifier in selected:
        source=inputs[identifier]
        row=dict(id=identifier,claim=source['claim'],reference='')
        tokens=shared.prompt_ids(tokenizer,row)
        if len(tokens)+384>16384:raise ValueError('Unexpected context overflow')
        row['expected_prompt_sha256']=common.digest(common.canonical(tokens));out.append(row)
        links.append(dict(id=identifier,GT=keys[identifier]['GT'],sid=keys[identifier]['sid'],
            old_panel=keys[identifier].get('old_panel'),full_prompt_sha256=source['expected_prompt_sha256'],
            empty_prompt_sha256=row['expected_prompt_sha256'],input_tokens=len(tokens)))
    if any(set(r)!={'id','claim','reference','expected_prompt_sha256'} or r['reference']!='' for r in out):
        raise ValueError('The only intended input edit is explicit reference removal')
    common.putl(a.out/'inputs160.jsonl',out);common.putl(a.out/'analysis_keys.jsonl',links)
    summary=dict(status='CPU_PREPARED_NO_GPU',N=160,patient_N=len({r['sid'] for r in links}),
        full_reference_predictions='reuse already saved107 and selected native candidate',
        intervention='same original claim and prompt, reference empty',original_GT_unchanged=True,
        training=False,selection_on_diagnostic_outputs=False,maximum_arms=2,
        max_input_tokens=max(r['input_tokens'] for r in links),API=0,GPU_started=False)
    common.put(a.out/'preparation.json',summary)
    public=ROOT/'outputs/129_native_reference_check';public.mkdir(parents=True,exist_ok=True)
    common.put(public/'preparation.json',summary)
    print(common.canonical(summary))


if __name__=='__main__':main()
