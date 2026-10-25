"""Author strata, invalid reasons and public-artifact verification; zero API."""
import json,ast,re
import common093 as c
from analyze093 import score
from report093 import table
def main():
    rows=c.lines(c.OUT/'predictions_public.jsonl');out=['# 093 作者分层与无效输出','','仅描述，不做新的子组优选。raw使用各自raw共同有效分母，PriorG使用三臂共同core。',''];result={}
    for panel in ['natural','pressure']:
        for author in ['human','llm']:
            rr=[r for r in rows if r['panel']==panel and r['author']==author];result[panel+'/'+author]={}
            for method,field in [('raw','raw_valid'),('PriorG','valid')]:
                z=score([r for r in rr if all(r['arms'][a][field] for a in ['B','F','A'])],method);result[panel+'/'+author][method]=z;out+=['## '+panel+'/'+author+'/'+method,'',table(z),'']
    invalid=[dict(id=r['id'],panel=r['panel'],GT=r['GT'],arms=r['arms']) for r in rows if not all(r['arms'][a]['valid'] for a in ['B','F','A'])]
    for r in invalid:
        out+=[f"无效ID `{r['id']}`，GT={r['GT']}："+str({a:{k:r['arms'][a][k] for k in ['status','parser_errors','native_errors','finish_reason','raw_valid']} for a in ['B','F','A']}),'']
    out+=['本轮两例三臂共享原body及回执；都有raw标签，但不满足core判定协议。保留原raw用于raw面板，不静默以旧结果补最终分数标签。完整N结果与core分母分列。','']
    for name,value in [('author_strata.json',result),('invalid_details.json',invalid)]:
        if (c.OUT/name).exists():assert c.read(c.OUT/name)==value
        else:c.put(c.OUT/name,value)
    (c.OUT/'author_strata.md').write_text('\n'.join(out),encoding='utf-8')
    forbidden={'text','claim','reference','body_text','reason','reasoning_content','api_key','content','messages'}
    def scan(v):
        if isinstance(v,dict):
            assert not (set(v)&forbidden),set(v)&forbidden
            for x in v.values():scan(x)
        elif isinstance(v,list):
            for x in v:scan(x)
    for p in c.OUT.rglob('*.json*'):
        value=c.lines(p) if p.suffix=='.jsonl' else c.read(p)
        if p.name=='decision.json':value={k:v for k,v in value.items() if k!='reason'} # authored study rationale, not native clinical reason
        scan(value)
    for p in c.TASK.glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    broken=[]
    for p in list(c.OUT.glob('*.md'))+list(c.TASK.glob('*.md')):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if not link.startswith(('http','#')) and not (p.parent/link.split('#')[0]).exists():broken.append([str(p),link])
    assert not broken,broken
    c.put(c.OUT/'supplement_selfcheck.json',dict(status='PASS',recursive_public_privacy=True,local_links=True,all_task_python_syntax=True,executor_selfcheck=True,independent_audit=False))
if __name__=='__main__':main()
