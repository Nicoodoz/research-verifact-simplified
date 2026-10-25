"""Prepare user-facing configuration tables and scientific plots from 078 results."""
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common078 as c
from analyze078 import NAMES,MAIN
def f(v,n=4):return '—' if v is None else f'{v:.{n}f}'
def tab(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def performance(rows):
 return tab(['实验配置','MCC ↑','PA ↑','正确数','错误支持数 ↓','回退数'],[[x['name'],f(x['MCC']),f(x['PA']*100,2)+'%',str(x['correct'])+'/'+str(x['n']),x['falseS'],x['fallback']] for x in rows])
def main():
 t=c.read(c.OUT/'tables.json');p=c.read(c.OUT/'paired_comparisons.json');co=c.read(c.OUT/'cohort_lists.json');ledger=c.read(c.OUT/'cost_ledger.json')
 # Keep the highest-PA prior-only ablation visible in the main display as well.
 prior_row=next(x for x in t['postprocessing_all'] if x['method']=='NS_prior')
 t['primary_all'].insert(7,prior_row)
 t['postprocessing_all'].insert(0,next(x for x in t['primary_all'] if x['method']=='Original'))
 s='# 078 完整配置性能表\n\nMCC、PA、AC1越高越好；错误支持数越低越好。每张表只比较相同ID与分母。主表统一使用预先登记的异常回退，随后列无回退的共同核心有效消融。作者原系统为官方R1-70B发布预测，不是重新调用现代模型冒充原系统。\n\n'
 titles={'primary_all':'主队列全体','primary_llm':'主队列LLM命题','primary_human':'主队列人写命题','primary_common_core':'主队列共同核心有效','bridge_all':'作者证据与C48桥接','bridge_llm':'桥接LLM命题','bridge_human':'桥接人写命题','bridge_common_core':'桥接共同核心有效','F4_all':'固定四例次级比较','F4_llm':'固定四例LLM命题','F4_human':'固定四例人写命题','F4_common_core':'固定四例共同核心有效','postprocessing_all':'后处理细分消融'}
 for key,title in titles.items():
  s+=f'## {title}（N={len(co[key])}）\n\n'+performance(t[key])+'\n'
 s+='## 类别召回与调用成本\n\n下表成本按登记单价折算历史/新增usage（DeepSeek 3/9、历史Qwen 3/12元每百万输入/输出token），为Judge平均调用成本，不含历史检索成本；回退时计入额外N-S调用，Gate计入触发的Qwen。它不等于078本轮新增收费。原系统没有可同比的当前服务账单，留空。\n\n'
 s+=tab(['配置','AC1','S召回','NS召回','NA召回','平均Judge元/条'],[[x['name'],f(x['AC1'])]+[f(x['recall'][k]*100,2)+'%' if x['recall'][k] is not None else '—' for k in c.c53.LABELS]+[f(x['judge_mean_cny'],5)] for x in t['primary_all']])
 s+='\n## 配对组件变化\n\n以下均为候选减对照；同任务内多组对比是开发消融，不把最高点自动升级为方法。\n\n'
 for key in ['primary_all','bridge_all','F4_all']:
  s+=f'### {titles[key]}\n\n'
  rows=[]
  for v in p[key]:
   m=v['metrics']['mcc'];a=v['metrics']['percent_agreement'];rows.append([NAMES[v['candidate']]+' − '+NAMES[v['base']],v['net'],v['delta_falseS'],f(m['delta']),f"[{m['ci95'][0]:.4f}, {m['ci95'][1]:.4f}]",f(a['delta']*100,2),f"[{a['ci95'][0]*100:.2f}, {a['ci95'][1]*100:.2f}]"])
  s+=tab(['比较','净正确','错误支持变化','ΔMCC','95%患者区间','ΔPA(pp)','95%患者区间(pp)'],rows)+'\n'
 s+='[逐例预测](predictions.jsonl) · [所有作者/有效性配对结果](paired_comparisons.json) · [费用](cost_ledger.json) · [组件来源](component_inventory.md)\n'
 (c.OUT/'performance_tables.md').write_text(s,encoding='utf-8',newline='\n')
 flat=[dict(cohort=key,method=x['method'],name=x['name'],N=x['n'],MCC=x['MCC'],PA=x['PA'],AC1=x['AC1'],correct=x['correct'],falseS=x['falseS'],fallback=x['fallback']) for key,v in t.items() for x in v]
 # JSON is the primary machine table; no spreadsheet artifact is needed.
 c.put(c.OUT/'compact_performance.json',flat,new=False)
 codes=[x['method'] for x in t['primary_all']];names=['Original','N-V','N-S raw','U2','U2 + Gate','StdM','StdV','N-S + prior','T-V','T-S raw','T-S + U2','T-S + PriorG']
 fig,axes=plt.subplots(1,3,figsize=(12,5),sharey=True);y=np.arange(len(codes));colors=['#888888']+['#377eb8']*(len(codes)-2)+['#e69f00']
 for ax,field,title in zip(axes,['MCC','PA','falseS'],['MCC (higher is better)','Accuracy (%)','False Supported (lower is better)']):
  val=[x[field]*(100 if field=='PA' else 1) for x in t['primary_all']];ax.barh(y,val,color=colors);ax.set_title(title);ax.spines[['top','right']].set_visible(False);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
 axes[0].set_yticks(y,names);axes[0].invert_yaxis();fig.suptitle('078 | Same 384 claims, 24 development patients',fontsize=13)
 fig.text(.01,.01,'Operational fallback disclosed; historical and new API responses. Not a new external or reserved test.',fontsize=8)
 fig.tight_layout(rect=(0,.04,1,.95));fig.savefig(c.OUT/'main_results.png',dpi=160);fig.savefig(c.OUT/'main_results.svg');plt.close(fig)
 print(c.canon(dict(status='PASS',tables=len(t),new_cost=ledger['estimated_usage_and_unknown_cny'])))
if __name__=='__main__':main()
