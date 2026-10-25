"""Render fixed 077 results without selecting new working points."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'outputs/077_static_example_discrimination'
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def table(h,rows):return '\n'.join(['| '+' | '.join(h)+' |','|'+'|'.join(['---']*len(h))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
def fmt(v):return '未定义' if v is None else f'{v:.4f}'
r=read('results.json');s=read('sensitivity.json')
text='# 077 数字附录\n\n所有行使用B/F4共同有效评分。AUC差为F4−B；区间按患者成组配对重采样。阶段与去重合并是不同口径，不相加为独立病例。全部结果属于已暴露development的事后诊断。\n\n## 全阶段及作者分层\n\n'
text+=table(['队列','N','患者','S–NS差','S–NA差','NS–NA差','平均AUC差','低风险混合包络差(pp)'],[[k,v['n'],v['patients']]+[fmt(v['auc']['pairs'][q]['delta']) for q in ['S_NS','S_NA','NS_NA']]+[fmt(v['auc']['macro']['delta']),f"{v['frontier']['families']['frozen_NS_NA']['delta']['low_risk_mean_mixed']*100:.3f}"] for k,v in r.items()])
text+='\n低风险摘要为0–20%错误支持率预算区间内的平均正确率；是经验最优曲线的描述，**不是实测部署准确率**。\n\n## 去重合并的完整预算比较\n\n'
rr=[]
for cohort in ['pooled_earliest','pooled_latest']:
 for fam,z in r[cohort]['frontier']['families'].items():
  for i,b in enumerate(r[cohort]['frontier']['risk_budgets']):
   ci=z['delta_intervals']['mixed'][i]['ci95'];rr.append([cohort,fam,f'{b*100:.0f}%',f"{z['B']['deterministic'][i]*100:.3f}",f"{z['F4']['deterministic'][i]*100:.3f}",f"{z['B']['mixed'][i]*100:.3f}",f"{z['F4']['mixed'][i]*100:.3f}",f"{z['delta']['mixed'][i]*100:.3f}",f'[{ci[0]*100:.3f}, {ci[1]*100:.3f}]'])
text+=table(['队列','NS/NA权重','风险上限','B确定性PA%','F4确定性PA%','B混合PA%','F4混合PA%','混合差pp','差值95%区间pp'],rr)
text+='\n## 去掉任务块\n\n'
text+=table(['口径','去掉任务块','N','平均AUC差','低风险混合差pp'],[[k,block,v['n'],fmt(v['macro']),f"{v['frontier']['frozen_NS_NA']*100:.3f}"] for k,z in s.items() for block,v in z['leave_task_block_out'].items()])
text+='\n## 区间有效性\n\nLLM子组仅1条NA，bootstrap抽不到其所在患者时S–NA、NS–NA和完整macro未定义；不补0.5，也不悄悄改为两类平均。下表保留实际有效重采样次数。\n\n'
text+=table(['队列','S–NS有效/1000','S–NA有效/1000','NS–NA有效/1000','完整macro有效/1000'],[[k]+[v['auc']['pairs'][q]['delta_interval']['valid_draws'] for q in ['S_NS','S_NA','NS_NA']]+[v['auc']['macro']['delta_interval']['valid_draws']] for k,v in r.items()])
text+='\n[完整结果与区间](results.json) · [全部单参数状态的公共评价结果](curve_states.json) · [留一患者](sensitivity.json) · [曲线独立核对](frontier_verification.json)\n'
(OUT/'numeric_appendix.md').write_text(text,encoding='utf-8',newline='\n')
fig,axes=plt.subplots(2,2,figsize=(11,7.4),sharey='row')
for j,cohort in enumerate(['pooled_earliest','pooled_latest']):
 z=r[cohort]['frontier']['families']['frozen_NS_NA']
 for i,lim in enumerate([.2,1.]):
  ax=axes[i,j]
  for arm,color in [('B','#377eb8'),('F4','#e69f00')]:
   env=z[arm]['envelope'];x=np.r_[env['mixed_x'],1];y=np.r_[env['mixed_y'],env['mixed_y'][-1]]
   ax.plot(x*100,y*100,label=arm+' mixture',color=color,lw=2)
   dx=np.r_[env['deterministic_x'],1];dy=np.r_[env['deterministic_y'],env['deterministic_y'][-1]]
   ax.step(dx*100,dy*100,where='post',color=color,alpha=.4,linestyle='--',label=arm+' deterministic')
  ax.set_xlim(0,lim*100);ax.set_ylim(15,86);ax.set_xlabel('False-S rate budget (%)');ax.set_title(cohort.replace('pooled_','').capitalize()+(' | 0-20%' if i==0 else ' | full range'));ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
  if j==0:ax.set_ylabel('Oracle-envelope accuracy (%)')
axes[0,0].legend(fontsize=8,frameon=False,loc='lower right');fig.suptitle('Fixed examples: local low-risk advantage, no uniform dominance',fontsize=13)
fig.text(.02,.015,'Development-only, GT-aware empirical envelopes; 262 valid claims, 16 patients. Not deployed or held-out performance.',fontsize=9)
fig.tight_layout(rect=(0,.04,1,.96));fig.savefig(OUT/'frontiers.png',dpi=160);fig.savefig(OUT/'frontiers.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(8,4.5));colors=['#377eb8','#e69f00'];x=np.arange(3)
for j,cohort in enumerate(['pooled_earliest','pooled_latest']):
 q=[r[cohort]['auc']['pairs'][k] for k in ['S_NS','S_NA','NS_NA']];d=np.array([v['delta'] for v in q]);ci=np.array([v['delta_interval']['ci95'] for v in q]);ax.errorbar(x+(j-.5)*.15,d,yerr=np.array([d-ci[:,0],ci[:,1]-d]),fmt='o',capsize=4,color=colors[j],label=cohort.replace('pooled_',''))
ax.axhline(0,color='#555',lw=.8);ax.set_xticks(x,['S vs NS','S vs NA','NS vs NA']);ax.set_ylabel('Pairwise AUC difference (F4 - B)');ax.set_title('No consistent improvement across label pairs');ax.legend(frameon=False);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'auc_differences.png',dpi=160);fig.savefig(OUT/'auc_differences.svg');plt.close(fig)
print('PASS: tables and figures rendered')
