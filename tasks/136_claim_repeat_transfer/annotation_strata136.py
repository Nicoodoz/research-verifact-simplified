"""Explain completed136 results by original doctor agreement, without relabeling."""
from pathlib import Path
from collections import Counter
import csv,gzip,json,sys
R=Path(__file__).resolve().parents[2];O=R/'outputs/136_claim_repeat_transfer'
sys.path.insert(0,str(R/'tasks/120_full_pool_sft'));from final_compare120 import paired,LABELS
def main():
 cohort=[json.loads(x) for x in (O/'full1817_predictions_sanitized.jsonl').read_text(encoding='utf-8').splitlines()]
 ids={r['id'] for r in cohort};assert len(ids)==len(cohort)==1817;meta={}
 with gzip.open(R/'data/00_raw/verifact-bhc/1.1.0/propositions/human_verdicts.csv.gz','rt',encoding='utf-8-sig',newline='') as stream:
  for row in csv.DictReader(stream):
   i=row['proposition_id']
   if i not in ids:continue
   votes=[row['verdict'+str(n)] for n in range(1,4)];assert all(v in LABELS for v in votes)
   assert i not in meta
   meta[i]=dict(GT=row['human_gt'],unanimous=max(Counter(votes).values())==3,
    initial_S_votes=votes.count('Supported'),adjudicated=bool(row['adjudicated_verdict'].strip()),
    any_uncertain=any(row['uncertain_flag'+str(n)].strip().lower()=='true' for n in range(1,4)))
 assert meta.keys()==ids and all(r['GT']==meta[r['id']]['GT'] for r in cohort)
 groups=dict(all=cohort,first_round_unanimous=[r for r in cohort if meta[r['id']]['unanimous']],
  first_round_disagreement=[r for r in cohort if not meta[r['id']]['unanimous']],
  adjudicated=[r for r in cohort if meta[r['id']]['adjudicated']],
  any_first_round_uncertain=[r for r in cohort if meta[r['id']]['any_uncertain']])
 result={}
 for name,rows in groups.items():
  if rows:
   result[name]=paired(rows,{r['id']:dict(verdict=r['full_pool120']) for r in rows},{r['id']:dict(verdict=r['claim_repeat']) for r in rows},'full_pool120')
 votes={}
 for n in range(4):
  rows=[r for r in cohort if r['GT']!='Supported' and meta[r['id']]['initial_S_votes']==n]
  votes[str(n)]=dict(non_S=len(rows),false_S120=sum(r['full_pool120']=='Supported' for r in rows),
   false_S136=sum(r['claim_repeat']=='Supported' for r in rows),
   avoided=sum(r['full_pool120']=='Supported' and r['claim_repeat']!='Supported' for r in rows),
   added=sum(r['full_pool120']!='Supported' and r['claim_repeat']=='Supported' for r in rows))
 output=dict(method='Original first-round physician agreement; finalGT retained; only target1817 metadata used',
  groups=result,initial_S_votes=votes,no_training_selection=True,no_label_exclusion=True,no_reweighting=True,new_API=0,new_inference=0,
  caution='Unanimity is not certified truth; disagreement is not label error. Groups overlap except the unanimity partition.')
 (O/'annotation_strata.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# 136：原医生一致度分层','','首轮一致不等于标注必然无误，分歧也不等于标签错误；除一致/分歧划分外，其余分组有重叠。','137训练顺序与样本已固定，本分析不回填训练，不改标签或删除分歧样本。','',
  '|分层|N|MCC 120→136|正确数 120→136|false-S 120→136/非S|S救回/误伤|NS救回/误伤|NA救回/误伤|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for name,x in result.items():
  old=x['scores']['full_pool120'];new=x['scores']['candidate'];c=x['changes']['by_class']
  lines.append(f"|{name}|{x['N']}|{old['mcc']:.4f}→{new['mcc']:.4f}|{old['correct']}→{new['correct']}|{old['false_S']}→{new['false_S']}/{new['non_S']}|"+'|'.join(f"{c[g]['rescued']}/{c[g]['harmed']}" for g in LABELS)+'|')
 lines+=['','首轮一致／有分歧是完整划分；裁定和uncertain分层与其重叠，不能相加。详细类别指标与矩阵见JSON。','']
 (O/'annotation_strata.md').write_text('\n'.join(lines),encoding='utf-8')
 print(json.dumps({k:dict(N=v['N'],delta_MCC=v['delta_MCC'],delta_correct=v['delta_correct'],delta_false_S=v['delta_false_S']) for k,v in result.items()},ensure_ascii=False))
if __name__=='__main__':main()
