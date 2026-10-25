"""Export publication figure: same800 native confusion matrices, no new analysis."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import common096 as c
O=c.OUT/'valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k'
def main():
    metrics=c.read(O/'main_metrics.json')['natural']['raw_common'];fig,axes=plt.subplots(1,3,figsize=(10,3.7),constrained_layout=True)
    for ax,(key,title) in zip(axes,[('Original','Original published'),('V4_raw','V4-B raw'),('R1_raw','R1-B raw')]):
        cm=np.asarray(metrics[key]['confusion_matrix']);row=cm.sum(1,keepdims=True);rate=cm/row;im=ax.imshow(rate,vmin=0,vmax=1,cmap='Blues')
        for i in range(3):
            for j in range(3):ax.text(j,i,f'{cm[i,j]}\n{rate[i,j]:.1%}',ha='center',va='center',fontsize=10,color='white' if rate[i,j]>.55 else 'black')
        ax.set(xticks=range(3),yticks=range(3),xticklabels=['S','NS','NA'],yticklabels=['S','NS','NA'],xlabel='Prediction',title=title)
    axes[0].set_ylabel('Physician GT');fig.suptitle('Natural panel: identical 800 claims / 84 patients\nRow percentages; no imputed R1 predictions',fontsize=12);fig.colorbar(im,ax=axes,shrink=.75,label='Fraction within GT class')
    fig.savefig(O/'native_confusion.png',dpi=220);fig.savefig(O/'native_confusion.svg');plt.close(fig)
    svg=O/'native_confusion.svg';svg.write_text('\n'.join(x.rstrip() for x in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8',newline='\n');print('FIGURE_READY')
if __name__=='__main__':main()
