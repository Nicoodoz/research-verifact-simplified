"""Produce tables and a static figure from the immutable 076 reconstruction."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/076_existing_results_synthesis'
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def write(n,s):(OUT/n).write_text(s,encoding='utf-8',newline='\n')
def table(headers,rows):
 return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,r))+' |' for r in rows])+'\n'
st=read('stage_results.json');pa=read('paired_decomposition.json');ab=read('fixed_postprocessing_ablation.json')
rows=[]
for stage,arms in st.items():
 for arm,d in arms.items():
  f=d['full_final'];r=d['raw_all_arms_common']
  rows.append([stage,arm,f['n'],f['correct'],f"{f['MCC']:.4f}",f['falseS'],r['n'],r['correct'],f"{r['MCC']:.4f}",len(d['invalid_ids'])])
s='# 076 数字附录\n\n自动生成自076统一重建。阶段主结果复现历史多臂共同有效分母；两臂分解使用各自共同有效分母。所有correct/net为命题计数；MCC三分类。正负号是候选减对照。\n\n## 全部执行阶段和方案\n\n'
s+=table(['阶段','臂','完整N','final正确','final MCC','false-S','raw多臂共同N','raw正确','raw MCC','本臂无效'],rows)
s+='\nB无示例；F4固定4例（071原E）；C4错配标签（071原C）；S6固定6例；D4原词汇动态4例；L4修正词汇动态4例；M4 BGE语义动态4例；F6固定4+固定2；H6固定4+动态2；R4固定4例加批注。跨阶段绝对分数不可当作方法增量。\n\n## 全部配对计数分解\n\n'
rows=[]
for stage,pairs in pa.items():
 for name,v in pairs.items():
  rows.append([stage,name,v['common_valid_n'],v['raw_common']['net'],v['base_post_net'],v['candidate_post_net'],v['differential_post_net'],v['fallback_involved_net'],v['full_final']['net'],v['full_final']['delta_falseS']])
s+=table(['阶段','比较','共同有效N','raw差','对照post净','候选post净','post差','回退涉及差','完整final差','false-S差'],rows)
s+='\n## 固定后处理消融（各臂自身有效分母）\n\n不重新拟合、不选择新赢家，不同臂有效N不同时不可直接相减。G-only=只加历史Supported偏置；prior-only=只用历史先验比；全部使用原分数地板与tie规则。\n\n'
s+=table(['阶段','臂','有效N','raw','score argmax','G-only','prior-only','PriorG','raw→final救回','raw→final伤害'],[[v['stage'],v['arm'],v['n']]+[v['ablation'][k]['correct'] for k in ['raw','score_argmax','G_only','prior_only','PriorG']]+[v['raw_to_final']['rescue'],v['raw_to_final']['harm']] for v in ab])
s+='\n所有患者/作者/类别分层、配对区间与ID保存在[配对分解](paired_decomposition.json)、[消融](fixed_postprocessing_ablation.json)和[去重结果](static_F4_deduplicated.json)。病例内容不在此重复复制。\n'
write('numeric_appendix.md',s)
sources=[]
for p in sorted((ROOT/'outputs').glob('0*/report.md')):
 if '036'<=p.parent.name[:3]<='075':sources.append(dict(task=p.parent.name,path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),use='published report; native reconstruction only for 071-075, stored ledger replay for 068'))
write('historical_reports.json',json.dumps(sources,ensure_ascii=False,indent=2)+'\n')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
keys=list(st);x=np.arange(len(keys));raw=[pa[k]['F4_minus_B']['raw_common']['net'] for k in keys];final=[pa[k]['F4_minus_B']['final_common']['net'] for k in keys]
fig,ax=plt.subplots(figsize=(10,4.8));w=.36
ax.bar(x-w/2,raw,w,label='Raw verdict (pairwise valid)',color='#377eb8');ax.bar(x+w/2,final,w,label='Frozen PriorG (same valid IDs)',color='#e69f00')
ax.axhline(0,color='#444',linewidth=.8);ax.set_xticks(x,[k.replace('_','\n') for k in keys]);ax.set_ylabel('F4 minus B: net correct claims');ax.set_title('Static examples: raw and final effects differ across stages');ax.legend(frameon=False,loc='upper right');ax.spines[['top','right']].set_visible(False);ax.set_ylim(-5,7)
for i,k in enumerate(keys):ax.text(i,-4.8,'N='+str(pa[k]['F4_minus_B']['common_valid_n']),ha='center',fontsize=8)
fig.text(.02,.015,'Historical development results; 071/072 overlap. 073 pilot full-system +2 includes +1 fallback (valid-only +1).',fontsize=8)
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(OUT/'stage_decomposition.svg');fig.savefig(OUT/'stage_decomposition.png',dpi=160);plt.close(fig)
print(json.dumps(dict(status='PASS',stages=len(st),historical_reports=len(sources),tables='numeric_appendix.md',figure='stage_decomposition.svg')))
