"""Compare native input effects and training-realization differences separately."""
from pathlib import Path
import argparse,json,sys
from records133 import R,Q,ARMS,read,rows,receipts,target_ids
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import metrics,paired,LABELS
sys.path.insert(0,str(R/'tasks/135_reason_first'));from analyze135 import collect
def put(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--scope',choices=['screen160','old500','full1817'],required=True);ap.add_argument('--bootstrap',action='store_true');args=ap.parse_args()
 done=read(Q/'evidence/shuffle_repeat/training_done.json');assert (done['steps'],done['consumed'])==(369,2945)
 keys,target=target_ids(args.scope);raw=receipts();sha=done['adapter_sha256']
 for arm in ARMS:
  for i,row in raw[arm].items():
   assert i in keys and row['adapter_sha256']==sha
 oldplain={r['id']:{'verdict':r['verdict']} for r in rows(R/'outputs/120_full_pool_sft/final369_1817_predictions_sanitized.jsonl')}
 oldrepeat={r['id']:{'verdict':r['claim_repeat']} for r in rows(R/'outputs/136_claim_repeat_transfer/full1817_predictions_sanitized.jsonl')}
 old={'plain104':oldplain,'claim_repeat':oldrepeat};coverage={};seed_comparison={};valid={}
 for arm in ARMS:
  available=target&raw[arm].keys();valid[arm]={i for i in available if raw[arm][i]['parsed']['valid']}
  coverage[arm]=dict(target_N=len(target),received_N=len(available),valid_N=len(valid[arm]),missing_ids=sorted(target-available),invalid_ids=sorted(available-valid[arm]))
  if valid[arm]:
   rs=[keys[i] for i in sorted(valid[arm])];new={i:{'verdict':raw[arm][i]['parsed']['verdict']} for i in valid[arm]}
   seed_comparison[arm]=paired(rs,old[arm],new,'original120' if arm=='plain104' else 'original136',bootstrap=args.bootstrap)
   coverage[arm]['PA_full_target_bounds']=[seed_comparison[arm]['scores']['candidate']['correct']/len(target),(seed_comparison[arm]['scores']['candidate']['correct']+len(target)-len(valid[arm]))/len(target)]
 joint=sorted(valid['plain104']&valid['claim_repeat']);rs=[keys[i] for i in joint]
 new={arm:{i:{'verdict':raw[arm][i]['parsed']['verdict']} for i in joint} for arm in ARMS}
 within=paired(rs,new['plain104'],new['claim_repeat'],'new_plain104',bootstrap=args.bootstrap) if rs else None
 old_effect=paired(rs,oldplain,oldrepeat,'old_plain104',bootstrap=args.bootstrap) if rs else None
 groups=dict(natural=[r for r in rs if r['old_panel']=='natural'],pressure=[r for r in rs if r['old_panel']=='pressure'],new1317=[r for r in rs if r['subset']=='new'],history103_180=[r for r in rs if r['history103_panel'] in ('natural','pressure')])
 panels={k:paired(v,new['plain104'],new['claim_repeat'],'new_plain104') for k,v in groups.items() if v}
 author={k:paired([r for r in rs if r['author']==k],new['plain104'],new['claim_repeat'],'new_plain104') for k in sorted({r['author'] for r in rs})}
 base=R/'.local_models/134_author_baselines';authors={a:collect([base/'bundle/results'/a,base/'evidence'/a]) for a in ['author_base9b','author_lora9b']}
 table_rows=rs or [keys[i] for i in sorted(valid['plain104'])]
 core=[r for r in table_rows if all(authors[a][r['id']]['parsed']['valid'] for a in authors)]
 tables={a:metrics(core,{r['id']:authors[a][r['id']]['parsed']['verdict'] for r in core}) for a in authors} if core else {}
 if core:
  tables['paper_r1']=metrics(core,{r['id']:r['paper_r1'] for r in core})
  for arm in ARMS:
   if all(r['id'] in valid[arm] for r in core):tables['shuffle_'+arm]=metrics(core,{r['id']:raw[arm][r['id']]['parsed']['verdict'] for r in core})
  tables['original120']=metrics(core,{r['id']:oldplain[r['id']]['verdict'] for r in core});tables['original136']=metrics(core,{r['id']:oldrepeat[r['id']]['verdict'] for r in core})
  for name,path,field in [('label_only107',R/'.local_models/116_research_cycle/baseline107_selection1817.jsonl','verdict'),('midpoint132',R/'outputs/132_midpoint_update/selection1817_predictions_sanitized.jsonl','midpoint132'),('extra_steps137',R/'outputs/137_extra_steps/full1817_predictions_sanitized.jsonl','extra_steps')]:
   lookup={r['id']:r[field] for r in rows(path)};tables[name]=metrics(core,lookup)
 result=dict(scope=args.scope,seed=118027,step=369,expected_N=len(target),coverage=coverage,seed_comparison=seed_comparison,within_new_seed=within,within_old_seed_on_same_IDs=old_effect,panels=panels,by_author=author,three_baseline_common_N=len(core),common_scores=tables,
  interpretation='One fixed training realization; no seed selection. Input effect is paired within model. Between-seed change is not assigned solely to shuffle order.',new_API=0)
 if within and old_effect:result['difference_of_input_point_effects']={k:within[k]-old_effect[k] for k in ['delta_MCC','delta_PA','delta_correct','delta_false_S']}
 O=R/'outputs/133_shuffle_repeat';put(O/(args.scope+'.json'),result)
 safe=[dict(keys[i],**{arm:(raw[arm][i]['parsed']['verdict'] if i in valid[arm] else None) for arm in ARMS}) for i in sorted(target)]
 (O/(args.scope+'_predictions_sanitized.jsonl')).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in safe),encoding='utf-8')
 print(json.dumps(dict(scope=args.scope,coverage={a:{k:v for k,v in coverage[a].items() if k.endswith('_N')} for a in ARMS},within_delta=None if within is None else {k:within[k] for k in ['delta_MCC','delta_correct','delta_false_S']}),ensure_ascii=False))
if __name__=='__main__':main()
