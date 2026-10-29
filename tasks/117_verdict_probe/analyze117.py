"""One compact paired result, reusing the project's established evaluation."""
from pathlib import Path
import argparse,sys,json
R=Path(__file__).resolve().parents[2];P=R/'.local_models/117_verdict_probe';O=R/'outputs/117_verdict_probe'
sys.path.insert(0,str(R/'tasks/105_brief_supervision'));import common105 as c
sys.path.insert(0,str(R/'tasks/116_research_cycle'));from analyze_scores116 import section

def main():
 p=argparse.ArgumentParser();p.add_argument('--fit',type=Path,required=True);p.add_argument('--name',default='probe_initial');a=p.parse_args()
 base={r['id']:r for r in c.rows(R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl')}
 keys={r['id']:r for r in c.rows(R/'.local_models/116_research_cycle/keys_selection1817.jsonl')}
 result=dict(name=a.name,primary='verdict_prefix',models={},new_GPU_in_analysis=False,confirmation40_used=False)
 for representation,filename in [('verdict_prefix','verdict_prefix_screen_predictions.jsonl'),('prompt_end','prompt_end_screen_predictions.jsonl'),('verdict_mlp','screen_predictions.jsonl')]:
  path=a.fit/filename
  if not path.exists():continue
  rows=c.rows(path);pred={r['id']:r for r in rows};assert len(pred)==len(rows)
  assert all(r['valid'] and r['GT']==keys[r['id']]['GT'] for r in rows)
  groups={v:[keys[r['id']] for r in rows if keys[r['id']]['old_panel']==v] for v in ['natural','pressure']}
  groups['screen_enriched']=[keys[r['id']] for r in rows]
  panels={name:section(k,base,pred) for name,k in groups.items()}
  result['models'][representation]=dict(N=len(rows),panels=panels)
  c.putl(O/(a.name+'_'+representation+'_predictions.jsonl'),[dict(r,baseline107=base[r['id']]['verdict']) for r in rows])
 if set(result['models'])=={'verdict_mlp'}:result['primary']='verdict_mlp'
 c.put(O/(a.name+'.json'),result)
 summary={m:{p:{k:v[k] for k in ['N','delta_MCC','delta_PA','delta_correct','delta_false_S']} for p,v in z['panels'].items()} for m,z in result['models'].items()}
 print(c.canonical(summary))
if __name__=='__main__':main()
