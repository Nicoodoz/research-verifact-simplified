import numpy as np
def metrics(y,p,probs=None):
    y=np.asarray(y,dtype=int);p=np.asarray(p,dtype=int);cm=np.bincount(3*y+p,minlength=9).reshape(3,3).astype(float);n=len(y);r=cm.sum(1);s=cm.sum(0);d=np.diag(cm);correct=int(d.sum());pa=correct/n
    div=lambda a,b:np.divide(a,b,out=np.zeros_like(a,dtype=float),where=b!=0)
    precision=div(d,s);recall=div(d,r);f1=div(2*precision*recall,precision+recall);den=np.sqrt((n*n-s@s)*(n*n-r@r));mcc=float((correct*n-r@s)/den) if den else 0.
    avg=(r+s)/(2*n);pe=float(np.sum(avg*(1-avg))/2);nonS=int(sum(y!=0));predS=int(sum(p==0));fs=int(sum((y!=0)&(p==0)))
    out=dict(N=n,correct=correct,PA=pa,MCC=mcc,AC1=(pa-pe)/(1-pe),Macro_F1=float(f1.mean()),precision=precision.tolist(),recall=recall.tolist(),F1=f1.tolist(),confusion_matrix=cm.astype(int).tolist(),false_S=fs,true_non_S=nonS,false_S_rate=fs/nonS if nonS else None,predicted_S=predS,false_discovery_S=fs/predS if predS else None)
    if probs is not None:
        q=np.asarray(probs);assert np.isfinite(q).all() and np.allclose(q.sum(1),1,atol=1e-5)
        conf=q.max(1);calpred=q.argmax(1);ece=0.
        for i in range(15):
            mask=(conf>=i/15)&(conf<(i+1)/15 if i<14 else conf<=1)
            if mask.any():ece+=float(mask.mean()*abs((calpred[mask]==y[mask]).mean()-conf[mask].mean()))
        out.update(NLL=float(-np.log(np.maximum(q[np.arange(n),y],1e-12)).mean()),Brier=float(np.square(q-np.eye(3)[y]).sum(1).mean()),ECE_15=ece)
    return out
