"""Freeze a service/budget pause without interpreting incomplete scientific results."""
from pathlib import Path
from collections import Counter
from unittest.mock import patch
import socket
import subprocess
import tempfile
import os
import common016 as c
from finish_io016 import ORIGINAL,FINAL,collect,base_labels

def export(out):
    values,attempts,total=collect();labels,provenance=base_labels(values)
    out.mkdir(parents=True)
    c.write_csv(out/'attempts.csv',attempts);c.write_csv(out/'canonical_provenance.csv',provenance)
    for role in ('v4_first','qwen'):
        c.write_csv(out/f'predictions_{role}.csv',[dict(proposition_id=pid,verdict=labels[pid][role]) for pid in sorted(labels) if role in labels[pid]])
    new=[a for a in attempts if a['epoch']=='finalization_001']
    norm=[dict(c.normalize(v['job'],v['receipt']),role=v['job']['role']) for v in values.values() if v['job']['kind']=='chat']
    c.write_lines(out/'normalized_responses.jsonl',norm)
    summary=dict(status='service_and_budget_pause_not_scientific_failure',V4_valid=sum('v4_first' in p for p in labels.values()),
        Qwen_valid=sum('qwen' in p for p in labels.values()),Qwen_missing=601-sum('qwen' in p for p in labels.values()),
        new_attempts=len(new),new_status_counts=dict(Counter(a['http_status'] for a in new)),
        additional_cost_or_reserved_cny=sum(a['charge_cny'] for a in new),whole_task_used_or_reserved_cny=total,
        unknown_reservations_cny=sum(a['charge_cny'] for a in attempts if 'unknown' in a['charge_basis']),cap_cny=40,
        repeat_calls=sum(a['role']=='v4_repeat' for a in attempts),review_calls=sum(a['role']=='independent_review' for a in attempts),
        GT_effects_evaluated=False,scientific_gate_evaluated=False,final_confirmation=False,reserved_test_used=False)
    c.write_json(out/'summary.json',summary);return summary

def close():
    checks=sorted((FINAL/'budget_history').glob('estimate_*.json'));budget=c.read(checks[-1])
    c.require(not budget['within_cap'],'Do not close a budget-feasible continuation as failed')
    with patch.object(socket.socket,'connect',side_effect=AssertionError('Network disabled')),patch.object(c,'evaluate',side_effect=AssertionError('Incomplete effects forbidden')),patch.object(c,'paired_compare',side_effect=AssertionError('Incomplete effects forbidden')):
        out=FINAL/'pause_001';s=export(out)
        c.require(s['repeat_calls']==s['review_calls']==0,'Unexpected review sends')
        c.require(s['Qwen_missing']>0,'Unexpected complete base')
        for name in ('handoff_001.json','recovery_001/handoff_001.json','v4_completion_001/handoff_001.json'):
            c.check_hashes(c.read(ORIGINAL/name)['files_sha256'])
        c.check_hashes(c.read(FINAL/'authority_001.json')['execution_sha256'])
        c.write_json(out/'stop.json',dict(created_utc=c.now(),reason='Latest real-request failure rate makes whole-task completion forecast exceed40 CNY',
            forecast_sha256=c.file_hash(checks[-1]),projected_total_cny=budget['projected_task_total_cny'],
            no_further_sends=True,existing_retry_states_retained_not_executed=True,all_inflight_drained=True,
            method_outcome='undetermined; incomplete paired cohort; do not label the hypothesis failed'))
        verification=FINAL/'verification_001';verification.mkdir()
        replay=verification/'replay';export(replay)
        names=[p.name for p in out.iterdir() if p.is_file() and p.name!='stop.json']
        c.require(all(c.file_hash(out/n)==c.file_hash(replay/n) for n in names),'Offline replay mismatch')
        paths=[(c.TASK/n).relative_to(c.ROOT).as_posix() for n in ('finish016.py','finish_io016.py','close_finish_pause016.py')]
        with tempfile.TemporaryDirectory(prefix='016-finish-checkout-') as temp:
            temp=Path(temp);env=dict(os.environ,GIT_INDEX_FILE=str(temp/'index'))
            def git(args):return subprocess.check_output(['git',*args],cwd=c.ROOT,env=env,stderr=subprocess.PIPE)
            git(['read-tree','HEAD']);git(['-c','core.autocrlf=false','add','--',*paths])
            dest=temp/'checkout';dest.mkdir();git(['-c','core.autocrlf=true','checkout-index','--prefix='+dest.as_posix()+'/','--',*paths])
            c.require(all((c.ROOT/n).read_bytes()==(dest/n).read_bytes() for n in paths),'Windows checkout mismatch')
        c.write_json(verification/'summary.json',dict(status='executor_self_check_only_not_independent_audit',network_blocked=True,effect_evaluation_blocked=True,
            old_handoffs_intact=True,all_receipts_costs_reconciled=True,successful_answers_not_repeated=True,replayed_files=len(names),
            windows_checkout_byte_identical_files=len(paths),unit_tests_passed=9,scientific_results_not_available=True))
    report=f'''# 016 当前状态：服务与预算阻塞

**本轮已按授权尝试续跑，但无法在现有服务状态和40元任务上限内完成，已停止新增发送。研究方法的成败仍未判定。**

## 实际进展

- 仍为原6名development患者、601条claim；C48和所有prompt保持冻结。
- V4有效回答 **{s['V4_valid']}/601**；Qwen有效回答 **{s['Qwen_valid']}/601**，尚缺 **{s['Qwen_missing']}** 条。
- 本轮首批8次真实请求：状态分布 **{s['new_status_counts']}**。HTTP 0表示通信超时／结果未知，不等于服务器确认未计费；对应费用预留全部保留。
- 旧成功回答、失败、停止锁及每次原始回执不改写；本轮成功回答纳入canonical结果，不重跑。
- 未启动ordinary repeat或independent-review，未读取GT进行效果评价；未使用剩余development或reserved test。

## 为什么停止

发送前将既往全部费用及未知预留结转¥11.38592123；按476个原始请求正文和历史服务器token校准、分歧复核预留与失败余量，预计全任务¥30.8590，可在预算内开始。

本轮追加usage估算及未知预留 **¥{s['additional_cost_or_reserved_cny']:.8f}**，任务累计 **¥{s['whole_task_used_or_reserved_cny']:.8f}/¥40**，其中未知预留¥{s['unknown_reservations_cny']:.8f}。不是账单核验。按这批真实请求的失败费用／成功率重新估算，全任务完成情景升至 **¥{budget['projected_task_total_cny']:.2f}**，因此停止。该数值是服务维持当前状态下的预算情景，不是已经花费的金额。

价格依据：[硅基流动价格](https://siliconflow.cn/pricing)，Qwen输入/输出3/12元每百万token，V4按高峰3/9规划；完整预估版本见`budget_history/`。不能因个别请求成功就认定服务已稳定恢复。

## 科研判断与续接边界

目前不能回答015信号是否复现、review是否优于repeat、作者／类别／患者增益或是否通过事前门槛。缺少完整配对数据，不能做available-case主分析，也不能把服务失败写成方法失败。原门槛（比最强单模型净≥13、比repeat净≥7及作者／类别／患者条件）保持，不降门槛。

未来续接应保留现有全部canonical回答与未知预留，从最新累计费用继续核算；服务稳定且全任务预计≤40后，方能补余下Qwen并运行分歧两臂。基础模型因服务中断跨时段运行，最终比较必须披露。当前未完成独立审计，也没有最终新患者确认。

## 审计入口

- [完整尝试与费用](pause_001/attempts.csv)、[canonical来源](pause_001/canonical_provenance.csv)、[当前汇总](pause_001/summary.json)、[停止依据](pause_001/stop.json)。
- [执行自查](verification_001/summary.json)：原handoff指纹、回执费用、结果重建及Windows检出一致；9项离线测试通过，均不是独立审计PASS。
- `handoff_001.json`登记HEAD、未提交状态、代码与成果指纹；本交付仅可审计续跑／停止完整性，不能审计尚不存在的016效果结论。
'''
    (FINAL/'report.md').write_text(report,encoding='utf-8',newline='\n')
    c.seal(out,[checks[-1],FINAL/'live/ledger.json'],[Path(__file__),c.TASK/'finish_io016.py'])
    c.write_json(ORIGINAL/'current_checkpoint_004.json',dict(created_utc=c.now(),**s,report='finalization_001/report.md',previous_checkpoint_sha256=c.file_hash(ORIGINAL/'current_checkpoint_003.json')))
    root=c.ROOT/'README.md';raw=root.read_bytes();parts=raw.split(b'\r\n\r\n',2)
    text=f"016按最新授权续跑Qwen后再次触发服务／预算停止：V4 601/601，Qwen {s['Qwen_valid']}/601；本轮8次真实请求仅{s['new_status_counts'].get(200,0)}次成功，通信超时记录完整保留。累计估算及未知预留¥{s['whole_task_used_or_reserved_cny']:.8f}/¥40，按当前失败率估算完成需约¥{budget['projected_task_total_cny']:.2f}，故未启动分歧复核或效果评价；科研成败未定。当前唯一必读[016续跑状态报告](outputs/016_disagreement_triggered_review_validation/finalization_001/report.md)。"
    c.require(len(parts)==3 and parts[1].decode('utf-8').startswith('016'),'README navigation changed unexpectedly')
    root.write_bytes(parts[0]+b'\r\n\r\n'+text.encode('utf-8')+b'\r\n\r\n'+parts[2])
    agents=c.ROOT/'AGENTS.md'
    with agents.open('ab') as f:f.write(('\r\n\r\n### 016最新续跑状态（2026-09-16）\r\n\r\n'+text+' 最新用户授权已解除此前Qwen禁发并允许分歧两臂，但此次服务／费用保护阻断后续。原历史状态与停止锁保持；未知费用不能清零。当前不能判断方法失败，未开展新患者确认。\r\n').encode('utf-8'))
    files=[p for p in FINAL.rglob('*') if p.is_file()]+[c.TASK/n for n in ('finish016.py','finish_io016.py','close_finish_pause016.py')]+[ORIGINAL/'current_checkpoint_004.json',c.ROOT/'tests/test_finish016.py']
    c.write_json(FINAL/'handoff_001.json',dict(created_utc=c.now(),HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),
        working_tree_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),independent_audit=False,
        scope='Continuation checkpoint, accounting and service/budget stop only; no complete016 scientific evaluation',
        files_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in files}))
    print(c.canonical(s))

if __name__=='__main__':close()
