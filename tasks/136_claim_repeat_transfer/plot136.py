"""Plot only the actual common-ID quality/risk results; no model fitting."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

R=Path(__file__).resolve().parents[2];O=R/'outputs/136_claim_repeat_transfer'
v=json.loads((O/'full1817.json').read_text(encoding='utf-8'))
scores=v['three_baseline_common_scores'];n=v['three_baseline_common_N']
order=['author_base9b','author_lora9b','paper_r1','label_only107','full_pool120','midpoint132','claim_repeat']
labels=['Base9B (original prompt)','LoRA9B (original prompt)','Paper R1-70B (historical)',
        '107 label-only (104 prompt)','120 final369 (104 prompt)','132 midpoint (104 prompt)','120 + claim repeat (104 prompt)']
colors=['#999999','#e69f00','#cc79a7','#0072b2','#56b4e9','#009e73','#d55e00']
assert all(scores[name]['n']==n for name in order)
denominators={scores[name]['non_S'] for name in order};assert len(denominators)==1
fig,ax=plt.subplots(figsize=(8,4.8))
for name,label,color in zip(order,labels,colors):
 m=scores[name];marker='X' if name=='paper_r1' else ('*' if name=='claim_repeat' else 'o')
 ax.scatter(100*m['false_S']/m['non_S'],m['mcc'],s=140 if name=='claim_repeat' else 70,
            marker=marker,color=color,label=label,edgecolors='white',linewidths=.65,zorder=3)
ax.set_xlabel('False-S / true non-S (%) — lower is better')
ax.set_ylabel('MCC — higher is better')
ax.set_title(f'Quality and risk on the same {n} items')
ax.grid(alpha=.22,zorder=0)
ax.spines[['top','right']].set_visible(False)
ax.legend(loc='upper left',bbox_to_anchor=(1.01,1),frameon=False,fontsize=8)
fig.text(.11,.01,f'20 previously exposed development patients; true non-S denominator = {next(iter(denominators))}.\nHistorical R1 uses a different model/system; prompt and supervision differences remain.',fontsize=8,color='#444444')
fig.subplots_adjust(left=.11,bottom=.19,right=.64,top=.90)
for suffix in ['png','svg']:
 path=O/('quality_risk.'+suffix);fig.savefig(path,dpi=220,bbox_inches='tight')
 if suffix=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
plt.close(fig)
print(json.dumps(dict(common_N=n,files=['quality_risk.png','quality_risk.svg'])))
