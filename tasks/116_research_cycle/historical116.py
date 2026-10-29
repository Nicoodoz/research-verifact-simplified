"""Same-ID historical180 references, without any new model calls."""
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tasks/109_boundary_replay'));import common109 as c
from analyze109 import metrics
P=R/'.local_models/116_research_cycle';O=R/'outputs/116_research_cycle'

def main():
    history=c.rows(R/'outputs/103_lora_selection/final_paired_predictions.jsonl')
    base={r['id']:r for r in c.rows(P/'baseline107.jsonl')}
    keys={r['id']:r for r in c.rows(P/'keys.jsonl')}
    assert len(history)==len({r['id'] for r in history})==180
    assert all(r['GT']==keys[r['id']]['GT'] for r in history)
    sources={'103_base9b':{r['id']:r['predictions']['nine_direct'] for r in history},
             '103_thinking9b':{r['id']:r['predictions']['nine_native'] for r in history},
             '103_lora9b':{r['id']:r['predictions']['nine_lora'] for r in history},
             '107_label_only':{r['id']:base[r['id']]['verdict'] for r in history},
             'paper_r1':{r['id']:r['paper_r1'] for r in history}}
    for name in c.read(O/'cycle_state.json')['completed_jobs']:
        if not (name.endswith('pilot') or name=='single_token_768'):continue
        p=O/(name+'_predictions.jsonl')
        if p.exists():sources[name]={r['id']:r['verdict'] for r in c.rows(p) if r.get('valid',True)}
    panels={}
    for panel in ['natural','pressure']:
        expected=[keys[r['id']] for r in history if r['panel']==panel]
        panels[panel]={}
        for name,pred in sources.items():
            rows=[r for r in expected if pred.get(r['id']) in c.LABELS]
            panels[panel][name]=dict(expected_N=len(expected),valid_N=len(rows),metrics=metrics(rows,pred))
    out=dict(scope='Original103 natural120 and pressure60 only',panels=panels,new_model_calls=0,
             caveat='103 uses its historical prompt/decoding and512-example training; later pipelines differ. Whole-recipe historical comparison, not a component ablation or complete1817 baseline.')
    c.put(O/'historical180.json',out);print('Historical180 references updated from existing predictions only')

if __name__=='__main__':main()
