"""Plot actual common-ID results after137 full evaluation is complete."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parents[2];O=R/'outputs/137_extra_steps'
v=json.loads((O/'full1817.json').read_text(encoding='utf-8'))
scores=v['three_baseline_common_scores'];n=v['three_baseline_common_N']
order=['author_base9b','author_lora9b','paper_r1','label_only107','full_pool120','midpoint132','claim_repeat136','extra_steps']
labels=['Base9B (original prompt)','LoRA9B (original prompt)','Paper R1-70B (historical)',
        '107 label-only (104 prompt)','120 final369 (104 prompt)','132 midpoint (104 prompt)',
        '136: 120 + claim repeat','137: extra 149 steps + claim repeat']
colors=['#999999','#e69f00','#cc79a7','#0072b2','#56b4e9','#009e73','#9467bd','#d55e00']
assert all(scores[name]['n']==n for name in order)
denominators={scores[name]['non_S'] for name in order};assert len(denominators)==1
fig,ax=plt.subplots(figsize=(8.8,5.2))
for name,label,color in zip(order,labels,colors):
 m=scores[name];marker='X' if name=='paper_r1' else ('*' if name=='extra_steps' else 'o')
 ax.scatter(100*m['false_S']/m['non_S'],m['mcc'],s=155 if name=='extra_steps' else 70,
            marker=marker,color=color,label=label,edgecolors='white',linewidths=.65,zorder=3)
ax.set_xlabel('False-S / true non-S (%) — lower is better')
ax.set_ylabel('MCC — higher is better')
ax.set_title(f'Quality and risk on the same {n} items')
ax.grid(alpha=.22,zorder=0);ax.spines[['top','right']].set_visible(False)
ax.legend(loc='upper left',bbox_to_anchor=(1.01,1),frameon=False,fontsize=8)
fig.text(.10,.01,f'Point estimates on 20 previously exposed development patients; true non-S = {next(iter(denominators))}.\nHistorical R1 uses a different model/system. Patient intervals and class tradeoffs are in the report.',fontsize=8,color='#444444')
fig.subplots_adjust(left=.10,bottom=.18,right=.63,top=.90)
for suffix in ['png','svg']:
 path=O/('quality_risk.'+suffix);fig.savefig(path,dpi=220,bbox_inches='tight')
 if suffix=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
plt.close(fig)
print(json.dumps(dict(common_N=n,files=['quality_risk.png','quality_risk.svg'])))
