"""Readable coverage, author strata and three-class tables from fixed outputs."""
import csv
import common100 as c
def fmt(x):return '—' if x is None else f'{x:.4f}'
def main():
 text=['# 100完整分类、覆盖与作者分层表','原始GT不变；自然和压力分开；完整N与共同有效分母分开。Original是作者历史R1预测，O才是同期同模型发布reference输入。']
 coverage=[];strata=[]
 for mode in ['development','confirmation','cross_model_confirmation']:
  p=c.OUT/(mode+'_analysis.json')
  if not p.exists():continue
  a=c.read(p)
  for panel,pp in a['panels'].items():
   text+=['## '+mode+' / '+panel,f"冻结{pp['frozen_N']}条，共同有效{pp['common_N']}条、{pp['patients']}人；GT={pp['GT']}。"]
   for arm,z in pp['coverage'].items():coverage.append([mode,panel,arm,z['frozen_N'],z['valid'],z['invalid'],z['known_correct']])
   for arm,t in pp['tables'].items():
    text+=['### '+arm,f"MCC={t['mcc']:.4f}，PA={t['percent_agreement']:.2%}，Macro-F1={t['Macro_F1']:.4f}，AC1={t.get('gwet_ac1',t.get('ac1'))}；false-S={t['false_S']}/{t['true_non_S']}，预测S假发现率={t['false_discovery_S']}。",
     '|GT类别|precision|recall|F1|GT数|','|---|---:|---:|---:|---:|']
    for i,lab in enumerate(c.LABELS):
     z=t['per_class'][lab];text.append(f"|{lab}|{fmt(z['precision'])}|{fmt(z['recall'])}|{fmt(z['f1'])}|{sum(t['confusion_matrix'][i])}|")
    text+=['混淆矩阵：行GT、列预测，顺序S/NS/NA。','|GT\\预测|S|NS|NA|','|---|---:|---:|---:|']
    text.extend('|'+lab+'|'+'|'.join(str(n) for n in row)+'|' for lab,row in zip(c.LABELS,t['confusion_matrix']))
   text+=['### human / LLM分层','|作者|配置|N|MCC|PA|正确|false-S/non-S|NS/NA召回|','|---|---|---:|---:|---:|---:|---:|---|']
   for author,tables in pp['by_author'].items():
    for arm,t in tables.items():
     text.append(f"|{author}|{arm}|{t['n']}|{t['mcc']:.4f}|{t['percent_agreement']:.2%}|{t['correct']}|{t['false_S']}/{t['true_non_S']}|{fmt(t['per_class']['Not Supported']['recall'])}/{fmt(t['per_class']['Not Addressed']['recall'])}|")
     strata.append([mode,panel,author,arm,t['n'],t['mcc'],t['percent_agreement'],t['correct'],t['false_S'],t['true_non_S']])
 (c.OUT/'detailed_tables.md').write_bytes(('\n\n'.join(text)+'\n').encode())
 for name,header,rows in [('coverage.csv',['stage','panel','arm','frozen_N','valid','invalid','known_correct_lower_bound'],coverage),('author_strata.csv',['stage','panel','author','arm','N','MCC','PA','correct','false_S','non_S'],strata)]:
  with (c.OUT/name).open('w',encoding='utf-8',newline='') as f:w=csv.writer(f,lineterminator='\n');w.writerow(header);w.writerows(rows)
 print('Detailed class, confusion, coverage and author tables written; no API')
if __name__=='__main__':main()
