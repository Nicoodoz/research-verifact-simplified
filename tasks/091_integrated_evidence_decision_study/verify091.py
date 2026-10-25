"""Read-only replay checks, independent matrix arithmetic, publication boundaries."""
from common091 import *
import re,subprocess,unittest,io
def independent(y,p):
    cm=[[0]*3 for _ in range(3)]
    for yy,pp in zip(y,p):cm[LABELS.index(yy)][LABELS.index(pp)]+=1
    n=len(y);r=[sum(v) for v in cm];c=[sum(cm[i][j] for i in range(3)) for j in range(3)];correct=sum(cm[i][i] for i in range(3));den=(n*n-sum(v*v for v in r))*(n*n-sum(v*v for v in c));po=[(r[i]+c[i])/(2*n) for i in range(3)];pe=sum(v*(1-v) for v in po)/2
    return dict(correct=correct,PA=correct/n,MCC=(n*correct-sum(a*b for a,b in zip(r,c)))/math.sqrt(den) if den>0 else 0.,AC1=(correct/n-pe)/(1-pe),Macro_F1=sum(2*cm[i][i]/(r[i]+c[i]) if r[i]+c[i] else 0 for i in range(3))/3,false_S=cm[1][0]+cm[2][0],confusion_matrix=cm)
def main():
    checks=0
    def check(ok,msg):
        nonlocal checks
        assert ok,msg;checks+=1
    d=read(OUT/'B_diagnosis.json');anchor=read(OUT/'historical_anchor_checks.json');inv=read(OUT/'C_material_inventory.json')
    for data in (d,anchor,inv):
        for rel,dig in data['source_sha256'].items():check(sha(ROOT/rel)==dig,rel)
    rows=lines(ROOT/'outputs/090_demo_constructor_repair_validation/predictions_public.jsonl');paths=lines(OUT/'B_case_paths.jsonl');rm={r['id']:r for r in paths}
    metric_rows=0
    for panel in ('natural','pressure'):
        z=[x for x in rows if x['panel']==panel and all(x['arms'][a]['valid'] for a in ARMS)]
        for a in ARMS:
            for m in METHODS:
                p=[prior_only(x['arms'][a]['scores']) if m=='prior_only' else x['labels'][a][m] for x in z];v=independent([x['GT'] for x in z],p);old=d['panels'][panel]['metrics'][a][m]
                for k,vv in v.items():check(abs(vv-old[k])<1e-12 if isinstance(vv,float) else vv==old[k],f'{panel}/{a}/{m}/{k}')
                metric_rows+=1
        for x in z:
            r=rm[x['id']];rd=int(x['labels']['P90']['raw']==x['GT'])-int(x['labels']['F4']['raw']==x['GT']);fd=int(x['labels']['P90']['PriorG']==x['GT'])-int(x['labels']['F4']['PriorG']==x['GT']);check((rd,fd)==(r['raw_delta'],r['final_delta']),'paired path')
        s=d['panels'][panel];check(sum(v['n'] for v in s['kind_counts'].values())==len(z),'partition')
        check(sum(x['final_delta'] for x in paths if x['panel']==panel)==s['metrics']['P90']['PriorG']['correct']-s['metrics']['F4']['PriorG']['correct'],'net identity')
        for a in ARMS:
            for before,after in (('raw','U0'),('U0','U2'),('U0','prior_only'),('prior_only','PriorG'),('raw','PriorG')):
                check(sum(x['n'] for x in s['class_transitions'] if x['arm']==a and x['before']==before and x['after']==after)==len(z),'transition total')
    r078=lines(ROOT/'outputs/078_component_ablation/predictions.jsonl')
    for m,old in anchor['table078'].items():
        v=independent([x['GT'] for x in r078],[x['methods'][m]['label'] for x in r078])
        for k,vv in v.items():check(abs(vv-old[k])<1e-12 if isinstance(vv,float) else vv==old[k],f'078/{m}/{k}')
        metric_rows+=1
    # 036: published aggregates only; never load reserved individual predictions/GT.
    report036=ROOT/'outputs/036_final_validation/report.md';section=report036.read_text(encoding='utf-8-sig').split('## 二、')[1].split('### 主要配对')[0];table={}
    for ln in section.splitlines():
        if not re.match(r'^\|(O|U0|U2|Gate_A|Std_M|Std_V)\|',ln):continue
        v=ln.strip('|').split('|');table[v[0]]=dict(correct=int(v[1].split('/')[0]),n=int(v[1].split('/')[1]),PA_percent=float(v[2]),MCC=float(v[3]),false_S=int(v[5]))
    check({k:v['correct'] for k,v in table.items()}==dict(O=2866,U0=2731,U2=2908,Gate_A=2886,Std_M=2999,Std_V=3004),'036 manuscript table')
    check(219-42==table['U2']['correct']-table['U0']['correct'],'036 RH');check(42+81==table['U2']['false_S']-table['U0']['false_S'],'036 HW')
    f=read(ROOT/'outputs/085_r1_70b_valdemardi/final_system_comparison.json');check(f['n']==180 and f['patients']==21,'085 scope')
    # C has no joined GT and no API execution artifacts.
    pool=lines(PRIVATE/'C_blind_pool.jsonl');check(len(pool)==17 and sum(x['missing'] for x in pool)==4 and inv['material_gate'] is False,'C material stop')
    check(all(not {'GT','scores','label','human_gt'}&set(x) for x in pool),'C blind schema');check(not (PRIVATE/'attempts').exists(),'no new paid calls')
    check(subprocess.check_output(['git','check-ignore',str(PRIVATE/'C_blind_pool.jsonl')],cwd=ROOT,text=True).strip()!='','private ignored')
    check(subprocess.check_output(['git','diff','HEAD','--','.gitignore'],cwd=ROOT)==b'','gitignore unchanged')
    # No new public clinical fields or copied claim/reference strings.
    sensitive=pool+lines(ROOT/'outputs/replays/090_demo_constructor_repair_validation/sample_blind.jsonl')
    snippets=[x[k].encode() for x in sensitive for k in ('claim','reference') if len(x[k])>=40]
    for p in list(OUT.rglob('*'))+list(TASK.rglob('*')):
        if not p.is_file() or p.suffix in ('.png','.svg'):continue
        b=p.read_bytes();check(not b.startswith(b'\xef\xbb\xbf'),'UTF8 no BOM');check(not any(t in b for t in snippets),f'clinical copy {p.name}')
    forbidden={'claim','reference','body_text','reasoning_content','api_key'}
    def scan(x):
        if isinstance(x,dict):
            bad=set(x)&forbidden
            # Frozen prior reference counts are numeric metadata, not EHR text.
            if bad=={'reference'} and x['reference']==list(COUNTS):bad=set()
            check(not bad,'public clinical schema')
            for v in x.values():scan(v)
        elif isinstance(x,list):
            for v in x:scan(v)
    for p in OUT.glob('*.json'):scan(read(p))
    for p in OUT.glob('*.jsonl'):
        for x in lines(p):scan(x)
    # All local document links must resolve; external URLs are separately sourced.
    for p in OUT.glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            check((p.parent/link.split('#')[0]).exists(),f'link {p.name}: {link}')
    import test091
    run=unittest.TextTestRunner(stream=io.StringIO()).run(unittest.defaultTestLoader.loadTestsFromModule(test091));check(run.wasSuccessful(),'unit tests')
    value=dict(status='PASS',checks=checks,unit_tests=run.testsRun,independent_metric_rows=metric_rows,independent_audit=False,API_calls=0,cost_cny=0,created_utc=now(),sources_036_085=bind([report036,ROOT/'outputs/036_final_validation/methods_and_settings.md',ROOT/'tasks/036_final_validation/protocol.md',ROOT/'outputs/085_r1_70b_valdemardi/report_formal.md',ROOT/'outputs/085_r1_70b_valdemardi/final_system_comparison.json',ROOT/'outputs/085_r1_70b_valdemardi/formal_reconciliation.json']),aggregate036=table)
    if (OUT/'selfcheck.json').exists():print(canonical(dict(status='PASS',checks=checks,replay=True)))
    else:put(OUT/'selfcheck.json',value);print(canonical(dict(status='PASS',checks=checks,unit_tests=run.testsRun,independent_metric_rows=metric_rows)))
if __name__=='__main__':main()
