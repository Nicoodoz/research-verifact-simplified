"""Paired standard-control contrasts on the already frozen development predictions."""
import sys
import numpy as np
import common036 as c
import evaluate036 as ev
def main():
    out=c.OUT/'development_supplement_001';assert not out.exists();data=c.read(c.ROOT/'outputs/035_lambda_boundary_calibration/run_002/inputs_numeric.json');aliases={'DS_to_Q':'bridge_qwen','Q_to_DS':'bridge_deepseek'};allpairs={};summaries=[]
    for folder in sorted((c.OUT/'development_001').iterdir()):
        f=folder/'frozen_predictions.npz'
        if not f.exists():continue
        name=folder.name;rr=data[aliases.get(name,name)];z=np.load(f,allow_pickle=False)
        for scope in ('all','human','llm'):
            ii=np.array([i for i,r in enumerate(rr) if scope=='all' or r['author']==scope]);rows=[rr[i] for i in ii]
            for m in ('Std_T','Std_G','Std_M','Std_V'):
                bp=z['U2_labels'][ii];p=z[m+'_labels'][ii]
                pair=ev.old.paired_compare(ev.old.cohort(rows),ev.old.predictions(rows,bp),ev.old.predictions(rows,p),iterations=1000);pair['probability_and_risk']=ev.a.paired_extra(rows,(bp,z['U2_logprob'][ii]),(p,z[m+'_logprob'][ii]));allpairs[name+'/'+scope+'/'+m+'-vs-U2']=pair
                summaries.append(dict(dataset=name,scope=scope,method=m,delta_PA=pair['metrics']['percent_agreement']['delta'],PA_ci95=pair['metrics']['percent_agreement']['ci95'],delta_MCC=pair['metrics']['mcc']['delta'],MCC_ci95=pair['metrics']['mcc']['ci95']))
    c.put(out/'paired.json',allpairs);c.csvwrite(out/'paired_summary.csv',summaries);c.put(out/'manifest.json',dict(created_utc=c.now(),files={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}));print('Development standard paired contrasts complete',flush=True)
if __name__=='__main__':main()
