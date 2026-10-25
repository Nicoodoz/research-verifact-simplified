"""Register user-approved extension and derive executor from tested 078 runner."""
import common078 as c
import run078

old = c.OUT
out = old / 'f4_extension_001'
plan = c.read(out/'proposed_plan.json')
run078.verify()
attempts, _ = run078.state()
spent = sum(a['cost_cny'] for a in attempts)
assert abs(spent-plan['old_spent_cny']) < 1e-10
assert c.sha(out/'main_jobs.jsonl') == plan['jobs_sha256']
for p,h in plan['source_sha256'].items():
    assert c.sha(c.ROOT/p) == h
text = (c.TASK/'run078.py').read_text(encoding='utf-8-sig')
text = text.replace('"""Append-only 078 executor; bounded recovery and whole-task 30-CNY ledger."""',
                    '"""078 F4 extension: original spend carried forward under approved cumulative 35 CNY cap."""')
text = text.replace('import common078 as c\n',
                    "import common078 as c\nc.OUT=c.OUT/'f4_extension_001'\nc.CAP=35.\n")
needle = "used=sum(a['cost_cny'] for a in attempts);inflight=0."
assert text.count(needle) == 1
text = text.replace(needle,"used=c.read(c.OUT/'authorization.json')['old_spent_cny']+sum(a['cost_cny'] for a in attempts);inflight=0.")
runner = c.TASK/'run_f4_extension.py'
with runner.open('x',encoding='utf-8',newline='\n') as f:
    f.write(text)
c.put(out/'authorization.json',dict(created_utc=c.now(),user_reply='补齐',
    interpretation='Approves immediately preceding proposal: cumulative078 cap35 CNY; complete fixed F4 to384 and disclose384/352/128 cohorts.',
    cap_cny=35,old_spent_cny=spent,estimated_new_cny=plan['estimated_new_cny'],
    price_checked_date='2026-09-24',price_source='https://help.aliyun.com/zh/model-studio/deepseek-v4-flash',
    snapshot='deepseek-v4-flash-0731',input_cny_per_million=3,output_cny_per_million=9,
    successful_outputs_not_repeated=True,postprocessing_refits=0))
sources=dict(plan['source_sha256'])
for p in [runner,c.TASK/'common078.py',c.TASK/'register_f4_extension.py',
          old/'predictions.jsonl',old/'cost_ledger.json',old/'postprocessing_frozen.json',
          old/'manifest.json',c.ROOT/'outputs/071_judge_icl_feasibility/freeze.json']:
    sources[p.relative_to(c.ROOT).as_posix()] = c.sha(p)
c.put(out/'freeze.json',dict(status='FROZEN_BEFORE_078_API',created_utc=c.now(),
    cap_cny=35,model=c.MODEL,new_jobs=256,reused_answers=128,
    source_sha256=sources,artifact_sha256={p.name:c.sha(p) for p in out.iterdir() if p.is_file()}))
print(c.canon(dict(status='FROZEN',old_spent_cny=spent,cap_cny=35,new_jobs=256)))
