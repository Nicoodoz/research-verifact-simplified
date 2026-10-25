"""Publish local016 result navigation and prepare an independent-audit handoff."""
from pathlib import Path
import subprocess
import common016 as c
from completion_io016 import ORIGINAL,OUT

def replace_first_paragraph(path,text,expected):
    raw=path.read_bytes();sep=b'\r\n\r\n' if b'\r\n' in raw else b'\n\n';parts=raw.split(sep,2)
    c.require(len(parts)==3 and parts[1].decode('utf-8').startswith(expected),'Navigation changed unexpectedly')
    path.write_bytes(parts[0]+sep+text.encode('utf-8')+sep+parts[2])

def main():
    c.require(not (OUT/'handoff_001.json').exists(),'Completion already handed off')
    c.check_manifest(OUT/'analysis_001');s=c.read(OUT/'analysis_001/summary.json');g=c.read(OUT/'analysis_001/gate.json')
    v=c.read(OUT/'verification_001/summary.json');c.require(v['external_calls']==0 and s['status']=='complete','Incomplete verification')
    state='达到原事前门槛，仅值得继续另行授权的后续冻结确认' if g['passed'] else '未达到原事前门槛，停止本方向，不做v2/v3或扩大'
    text=f"016已完成现有6名development患者601条验证：V4/Qwen均完整，{s['disagreements']}条分歧各完成ordinary repeat和015原版independent-review。review较最强单模型净{g['net_vs_best_single']:+d}条、较repeat净{g['net_vs_controls']['cross_repeat']:+d}条；{state}。累计usage估算及未知预留¥{s['task_used_or_reserved_cny']:.8f}/¥40。Qwen保留127条硅基流动回答＋474条阿里云回答，基础模型跨时段，相关限制已披露。当前唯一必读[016中文主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md)；执行自查通过，待独立审计。"
    replace_first_paragraph(c.ROOT/'README.md',text,'016')
    short=text.replace('(outputs/','(../outputs/')
    replace_first_paragraph(c.ROOT/'reviews/README.md',short,'016')
    with (c.ROOT/'AGENTS.md').open('ab') as f:
        f.write(('\r\n\r\n### 016完成后的当前边界（2026-09-16）\r\n\r\n'+text+' 本轮未使用剩余十名development或reserved test；未进行后续最终确认。原协议、所有历史run、失败、未知预留与审计意见保持。新结果位于completion_002；旧报告中的停止状态均为其版本快照。\r\n').encode('utf-8'))
    pointer='# 016当前结果入口\n\n现有016已完成；唯一必读主报告：[completion_002/report.md](../../outputs/016_disagreement_triggered_review_validation/completion_002/report.md)。\n\n原任务README、历史报告及handoff保留冻结字节。本结果待独立审计；后续边界和科研判断以新报告为准。\n'
    (c.TASK/'current_result.md').write_text(pointer,encoding='utf-8',newline='\n')
    c.write_json(ORIGINAL/'current_checkpoint_006.json',dict(created_utc=c.now(),status='completed_awaiting_independent_audit',claims=601,
        V4=601,Qwen=601,disagreements=s['disagreements'],repeat=s['disagreements'],independent_review=s['disagreements'],
        whole_task_used_or_reserved_cny=s['task_used_or_reserved_cny'],cap_cny=40,gate_passed=g['passed'],
        conclusion=s['conclusion'],report='completion_002/report.md',all_paid_calls_stopped=True,
        next_stage_not_run=True,reserved_test_used=False,previous_checkpoint_sha256=c.file_hash(ORIGINAL/'current_checkpoint_005.json')))
    handoff='''# 016独立审计交接

本次交审对象：`completion_002/report.md`及其机器结果。执行者未宣布独立审计PASS。

## 必核范围

1. 原601条队列与003第25–30名开发患者，完整C48与015 evidence_only原版prompt；无新患者或隐藏Judge字段。
2. 跨供应商／时段偏差按调用前登记披露：V4旧601全部保留；Qwen硅基流动127＋阿里云474（含原测试1条），不重生成成功回答。
3. 全部V4/Qwen分歧的两臂覆盖、原ordinary repeat完整body相等、候选答案不进入review、共同标签原样保留。
4. `analysis_001/`002指标、配对患者bootstrap、类别／患者代价、原gate代码，以及部署调用／成本对照。
5. 016从最早检索开始跨所有账号、供应商、失败和测试的累计费用；未知预留不释放。`attempts.csv`每个回执可回查。
6. 断网重放与真正Windows检出；正常顶层导航变化不阻断旧历史，而请求、代码、回执、协议和结果须严格。

## 离线入口

`python -B tasks/016_disagreement_triggered_review_validation/verify_completion016.py --output <全新验证目录>`

`python -B tasks/016_disagreement_triggered_review_validation/analyze_completion016.py --output <全新分析目录>`

`python -B -m unittest discover -s tests -p test*016.py`

`python -B -m unittest discover -s tests -p test_aliyun.py`

日常验证不需密钥或网络。既有verification_001不覆盖，审计使用新的目录。本轮complete016续跑入口在completion_002/analysis_001存在后禁止新增发送。

handoff_001.json记录实际HEAD、未提交状态、内容与代码指纹。顶层README/AGENTS/reviews索引及.gitattributes的哈希单列为可变导航快照，不作为计算重放依赖；历史016自己的README和所有报告仍严格冻结。独立审计期间停止改动被审成果。
'''
    (OUT/'audit_handoff.md').write_text(handoff,encoding='utf-8',newline='\n')
    files=[p for p in ORIGINAL.rglob('*') if p.is_file()]+[p for p in c.TASK.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [c.ROOT/n for n in ('src/verifact_research/inference/aliyun.py','scripts/run_aliyun.py','tests/test_aliyun.py','tests/test_completion016.py','tests/test_finish016.py','tests/test_review_validation016.py')]
    files += list((c.ROOT/'docs/aliyun').glob('*'))
    navigation=[c.ROOT/n for n in ('README.md','AGENTS.md','reviews/README.md','.gitattributes')]
    c.write_json(OUT/'handoff_001.json',dict(created_utc=c.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
        working_tree_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),independent_audit=False,
        files_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in files},
        mutable_navigation_snapshot={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in navigation}))
    print(c.canonical(dict(status='ready_for_independent_audit',gate_passed=g['passed'],task_cost=s['task_used_or_reserved_cny'],files=len(files))))

if __name__=='__main__':main()
