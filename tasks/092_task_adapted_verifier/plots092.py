import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import common092 as c
def main():
    m=c.read(c.OUT/'metrics.json')['full_OOF'];fig,axes=plt.subplots(1,3,figsize=(11,3.6),constrained_layout=True)
    for ax,name in zip(axes,['Original','frozen','finetuned']):
        cm=np.asarray(m[name]['confusion_matrix']);pct=cm/np.maximum(cm.sum(1,keepdims=True),1);ax.imshow(pct,cmap='Blues',vmin=0,vmax=1)
        for i in range(3):
            for j in range(3):ax.text(j,i,f'{cm[i,j]}\n{pct[i,j]:.1%}',ha='center',va='center',color='white' if pct[i,j]>.55 else 'black',fontsize=9)
        ax.set_xticks(range(3),['S','NS','NA']);ax.set_yticks(range(3),['S','NS','NA']);ax.set_xlabel('Prediction');ax.set_ylabel('Physician GT');ax.set_title(f"{name}\nPA {m[name]['PA']:.1%}; MCC {m[name]['MCC']:.3f}")
    fig.savefig(c.OUT/'confusion_matrices.png',dpi=180);fig.savefig(c.OUT/'confusion_matrices.svg');plt.close(fig)
if __name__=='__main__':main()
