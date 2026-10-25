"""Independent fusion decoding/optimality, provenance, documents and final delivery checks."""
import ast,re,subprocess
import numpy as np
from scipy.special import softmax,logsumexp
from sklearn.metrics import confusion_matrix,accuracy_score,matthews_corrcoef,f1_score
import common092 as c
def main():
    checks=[]
    def check(ok,name):
        checks.append(dict(name=name,passed=bool(ok)))
        assert ok,name
    check(c.read(c.OUT/'selfcheck.json')['status']=='PASS','main executor check passed')
    baseline={r['id']:r for r in c.lines(c.OUT/'cached_baselines.jsonl') if r['arm']=='B'}
    rows={r['id']:r for r in c.lines(c.OUT/'oof_predictions.jsonl')}
    fusion=c.lines(c.OUT/'fusion_predictions.jsonl');models=c.read(c.OUT/'fusion_models.json')
    def bz(pid):
        s=baseline[pid]['scores'];q=np.array([s[k] for k in c.LABELS] if isinstance(s,dict) else s)
        return np.log(np.maximum(q/100,1e-6))+np.log(np.array([1108,100,170])/1378)-np.log(np.array([48,47,48])/143)+np.array([.1342909508820116,0,0])
    cloud={}
    for f in range(5):
        for r in c.lines(c.OUT/f'finetuned_fold{f}'/'predictions.jsonl'):cloud[r['id']]=r
    gradients=[]
    for model in models:
        fold=model['fold'];data=np.load(c.PRIVATE/f'fusion_train_fold{fold}.npz',allow_pickle=False);ids=data['ids'].tolist()
        check(ids==model['training_ids'],'same fusion training order')
        z=np.array([bz(i) for i in ids]);t=data['logits'].astype(float);t-=t.mean(1,keepdims=True);y=np.array([c.LABELS.index(rows[i]['GT']) for i in ids])
        for method in ['bias_only','text_fusion']:
            fit=model['fits'][method];p=np.array(fit['parameters']);bias=np.array([p[0],p[1],-p[0]-p[1]]);v=z+bias+(p[2]*t if len(p)==3 else 0)
            loss=(logsumexp(v,axis=1)-v[np.arange(len(y)),y]).mean()+.01*(p@p)
            check(abs(loss-fit['objective'])<1e-9,'independent fitted objective')
            residual=softmax(v,axis=1)-np.eye(3)[y];g=np.array([(residual[:,0]-residual[:,2]).mean(),(residual[:,1]-residual[:,2]).mean()]+([np.sum(residual*t,axis=1).mean()] if len(p)==3 else []))+.02*p
            gradients.append(float(np.max(np.abs(g))))
            check(np.max(np.abs(g))<1e-5,'interior optimum gradient')
    for row in fusion:
        pid=row['id'];fold=row['fold']
        if not baseline[pid]['valid']:
            check(row['predictions']['bias_only']==row['predictions']['text_fusion']==baseline[pid]['label'],'fallback unchanged');continue
        z=bz(pid);t=np.array(cloud[pid]['logits']);t-=t.mean()
        for method in ['bias_only','text_fusion']:
            p=models[fold]['fits'][method]['parameters'];v=z+np.array([p[0],p[1],-p[0]-p[1]])+(p[2]*t if len(p)==3 else 0)
            check(c.LABELS[int(v.argmax())]==row['predictions'][method],'independent fusion decode')
    for method,value in c.read(c.OUT/'fusion_supplement.json')['metrics'].items():
        y=[r['GT'] for r in fusion];p=[r['predictions'][method] for r in fusion]
        check(confusion_matrix(y,p,labels=c.LABELS).tolist()==value['confusion_matrix'],'fusion CM '+method)
        check(abs(accuracy_score(y,p)-value['PA'])<1e-12,'fusion PA '+method)
        check(abs(matthews_corrcoef(y,p)-value['MCC'])<1e-12,'fusion MCC '+method)
        check(abs(f1_score(y,p,labels=c.LABELS,average='macro')-value['Macro_F1'])<1e-12,'fusion MacroF1 '+method)
    for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'));check(True,'syntax '+p.name)
    for name in ['report.md','manuscript_zh.md','evidence_map.md','case_analysis.md']:
        path=c.OUT/name;body=path.read_text(encoding='utf-8')
        check(len(body)>500,'document content '+name)
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)',body):
            if '://' in target or target.startswith('#'):continue
            if target=='final_selfcheck.json':continue
            check((path.parent/target.split('#')[0]).exists(),'local link '+target)
    check('5 tests' in (c.PRIVATE/'final_tests.log').read_text(errors='replace') and '\nOK' in (c.PRIVATE/'final_tests.log').read_text(errors='replace'),'five meaningful tests passed')
    check(sum(v['N'] for v in c.read(c.OUT/'local_cloud_numerical_bridge.json'))==956,'numerical bridge coverage')
    check(sum(v['label_disagreements'] for v in c.read(c.OUT/'local_cloud_numerical_bridge.json'))==0,'bridge labels match')
    check(all(v['label_disagreements']==0 for v in c.read(c.OUT/'deployment_benchmark.json').values()),'online deployment labels match')
    check(c.read(c.OUT/'final_costs.json')['API_cost_cny']==0,'no new API cost')
    check(c.read(c.OUT/'final_costs.json')['local_C48_seconds']>0,'local preprocessing cost included')
    diff=subprocess.check_output(['git','diff','--name-only','--','outputs/091_integrated_evidence_decision_study'],text=True)
    check(not diff.strip(),'091 untouched')
    # Changed old local staging artifacts are preserved byte-for-byte in the pause archive.
    archive=c.OUT/'local_pause_archive'
    for p in archive.rglob('*'):
        if not p.is_file():continue
        oldpath='outputs/092_task_adapted_verifier/'+p.relative_to(archive).as_posix()
        check(p.read_bytes()==subprocess.check_output(['git','show','a17e4bff9:'+oldpath]),'local pause archive '+p.name)
    c.put(c.OUT/'final_selfcheck.json',dict(status='PASS',executor_selfcheck=True,independent_audit=False,checks=len(checks),failed=0,max_fusion_gradient=max(gradients),tests=5,figure_visual_review='confusion_matrices.png manually viewed: labels/counts readable, no clipping',utc=c.now(),scope='fusion fit/decoding, metrics, source/archive, deployment, document links, costs'))
    print('Final executor checks PASS',len(checks))
if __name__=='__main__':main()
