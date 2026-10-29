"""Build only missing103 trigger inputs, using frozen111 labels and original103 text."""
from pathlib import Path
from collections import Counter
import sys,json,itertools,tarfile
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tasks/109_boundary_replay'));import common109 as c
from rule112 import disagreement_vote,LABELS
sys.path.insert(0,str(ROOT/'tasks/103_lora_selection'));from prompt103 import messages
from analyze109 import metrics
P=ROOT/'.local_models/112_disagreement_vote';O=ROOT/'outputs/112_disagreement_vote'
def main():
    P.mkdir(exist_ok=True);O.mkdir(parents=True,exist_ok=True)
    keys=c.rows(ROOT/'outputs/111_half_extension/cohort_metadata.jsonl');ids={r['id'] for r in keys};assert len(ids)==len(keys)==1817
    data={a:{} for a in ['label_only107','update_half']}
    for r in c.rows(ROOT/'outputs/111_half_extension/predictions_sanitized.jsonl'):
        if r['arm'] in data:
            assert r['valid'] and r['id'] not in data[r['arm']];data[r['arm']][r['id']]=r['verdict']
    assert all(set(v)==ids for v in data.values())
    history=[r for r in c.rows(ROOT/'outputs/103_lora_selection/final_paired_predictions.jsonl') if r['local180']]
    cached={r['id']:dict(id=r['id'],verdict=r['predictions']['nine_lora'],valid=r['predictions']['nine_lora'] in LABELS,source='original103_final_paired_predictions') for r in history}
    assert len(cached)==180 and set(cached)<=ids
    keymap={r['id']:r for r in keys}
    assert all(r['GT']==keymap[r['id']]['GT'] and str(r['sid'])==str(keymap[r['id']]['sid']) for r in history)
    trigger={i for i in ids if data['label_only107'][i]!=data['update_half'][i]};missing=trigger-set(cached)
    assert (len(trigger),len(trigger&set(cached)),len(missing))==(166,28,138),'Locate ID discrepancy before changing scope'
    for a,b,d in itertools.product(LABELS,repeat=3):
        v,_=disagreement_vote(a,b,d);counts=Counter([a,b,d]);want=max(counts,key=counts.get) if max(counts.values())>1 else a
        assert v==want
    for a,b in itertools.product(LABELS,repeat=2):assert disagreement_vote(a,b,None)[0]==a
    raw={r['id']:r for r in c.rows(ROOT/'.local_models/103_lora_selection/eligible.jsonl') if r['id'] in missing}
    assert set(raw)==missing and all(r['role']=='selection' for r in raw.values())
    inputs=[dict(id=i,claim=raw[i]['claim'],reference=raw[i]['reference'],messages=messages(raw[i]['claim'],raw[i]['reference'],'label')) for i in sorted(missing)]
    c.putl(P/'inputs.jsonl',inputs);c.putl(P/'keys.jsonl',keys);c.putl(P/'cached103.jsonl',list(cached.values()))
    c.putl(P/'frozen_labels.jsonl',[dict(id=i,baseline=data['label_only107'][i],half=data['update_half'][i]) for i in sorted(ids)])
    checks={}
    for panel in ['natural','pressure']:
        rr=[r for r in history if r['panel']==panel];pred={r['id']:disagreement_vote(data['label_only107'][r['id']],data['update_half'][r['id']],cached[r['id']]['verdict'])[0] for r in rr};checks[panel]=metrics(rr,pred)
    assert abs(checks['natural']['percent_agreement']-88/120)<1e-12 and checks['natural']['false_S']==4 and abs(checks['natural']['mcc']-.4246)<.0001
    assert abs(checks['pressure']['percent_agreement']-37/60)<1e-12 and checks['pressure']['false_S']==8 and abs(checks['pressure']['mcc']-.3675)<.0001
    adapter=ROOT/'.local_models/103_lora_selection/gpu_results/qwen3.5-9b/train/checkpoint-512'
    assert c.read(adapter/'adapter_config.json')['r']==16
    cfg=dict(task=112,rule='disagreement_vote',baseline='label_only107',third='original103_nine_lora',trigger_N=len(trigger),missing103_N=len(missing),cached_trigger_N=28,cohort_N=1817,
        hourly_CNY=1.58,cap_CNY=1,task_start_beijing='2026-10-29 16:17:24',adapter_sha256=c.sha(adapter/'adapter_model.safetensors'),adapter_path='/root/autodl-tmp/verifact112/adapter103',
        decoding=dict(max_new_tokens=768,do_sample=False,repetition_penalty=1.,use_cache=True,thinking=False,reasoning_effort='low',parser='parse_label103.parse_label'),batch_size=2,no_shutdown=True,no_new_training=True,no_new_paid_API=True)
    c.put(ROOT/'tasks/112_disagreement_vote/config.json',cfg);c.put(P/'config.json',cfg)
    c.put(O/'preparation.json',dict(task=112,cohort_N=1817,agreement_N=1651,trigger_N=166,trigger_fraction=166/1817,cached_trigger_N=28,missing103_N=138,truth_table_cases=27,invalid_third_cases=9,disagreement_invalid_fallback_cases=6,
        historical180_check={k:dict(MCC=v['mcc'],PA=v['percent_agreement'],correct=v['correct'],false_S=v['false_S'],non_S=v['non_S']) for k,v in checks.items()},GT_not_in_rule_or_GPU_inputs=True,new105_work=False))
    with tarfile.open(P/'inputs112.tar.gz','w:gz',compresslevel=1) as tar:
        for name in ['inputs.jsonl','config.json']:tar.add(P/name,arcname=name,recursive=False)
    print(c.canonical(c.read(O/'preparation.json')))
if __name__=='__main__':main()
