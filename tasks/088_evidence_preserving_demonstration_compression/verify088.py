"""Read-only closed-task verification; never call a provider or write results."""
import subprocess
from common088 import *
import api088 as api

def main():
    f=read(OUT/'constructor_freeze.json');d=read(OUT/'demonstration_freeze.json');decision=read(OUT/'decision.json')
    for rel,digest in f['sources'].items():assert sha(ROOT/rel)==digest,rel
    for rel,digest in d['files'].items():assert sha(OUT/rel)==digest,rel
    t=read(OUT/'templates.json');assert len({h(v) for v in t['systems'].values()})==1
    assert h(t['systems']['F4'])==decision['F4_P4_Q4_system_sha256']
    assert decision['target_n']==decision['main_calls']==decision['source_review_calls']==decision['Q_constructor_calls']==0
    assert decision['quality_effect']=='NOT_EVALUATED' and decision['clinical_performance'] is None
    original=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');demos=read(OUT/'demonstrations.json');units=read(OUT/'source_units.json')
    for arm in ARMS:
        for ex,got in zip(original,demos[arm]):
            assert ex==got
            src=units[ex['proposition_id']];assert source_check(ex['reference'],src,[x['id'] for x in src['units']],got['reference'])
    rows,s,count=api.state();assert len(rows)==len(s)==2 and all(v==1 for v in count.values())
    for row in rows:
        assert row['phase']=='construct' and row['arm']=='P4' and row['http_status']==200
        req=read(ROOT/row['request_source']);tr=read(ROOT/row['receipt_source'])['transport'];native=json.loads(tr['body_text'])
        assert native['model']==BUILDER and json.loads(native['choices'][0]['message']['content'])['preserve_full'] is True
        assert req['job']['body']['model']==BUILDER and req['created_utc']>=f['created_utc']
    cost=read(OUT/'cost_ledger.json');assert abs(sum(x['cost_or_unknown_cny'] for x in rows)-cost['total_original_or_unknown_cny'])<1e-12
    assert cost['total_original_or_unknown_cny']<2<=20
    assert not (OUT/'main_jobs.jsonl').exists() and not (OUT/'main_freeze.json').exists()
    changed=subprocess.check_output(['git','-c','core.quotepath=false','diff','--name-only',f['head']],cwd=ROOT,text=True,encoding='utf-8').splitlines()
    allowed={'.gitattributes','AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/API_POLICY.md','docs/RESEARCH_EXECUTION.md','docs/REPRODUCIBILITY.md',
             'docs/088_Codex_保留判定依据的固定示例压缩_执行提示词.md'}
    assert all(x in allowed or x.startswith(('tasks/088_evidence_preserving_demonstration_compression/','outputs/088_evidence_preserving_demonstration_compression/')) for x in changed)
    oldattr=subprocess.check_output(['git','show',f['head']+':.gitattributes'],cwd=ROOT);newattr=(ROOT/'.gitattributes').read_bytes()
    assert newattr.startswith(oldattr)
    suffix=newattr[len(oldattr):].decode('utf-8').replace('\r\n','\n').strip()
    assert suffix in ('','# Preserve the frozen 088 task instruction bytes.\ndocs/088_* -text')
    assert '.gitignore' not in changed
    print(canonical(dict(status='PASS',constructor_calls=2,main_calls=0,no_historical_mutations=True,original_cny=cost['total_original_or_unknown_cny'],independent_audit=False)))

if __name__=='__main__':main()
