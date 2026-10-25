"""Runtime-only reconciliation and handoff; deliberately never reads GT."""
import csv,sys,collections
import common096 as c
import marlin096 as m
def main():
    m.activate();O=m.O;P=m.P;jj=m.r.jobs();done=[j for j in jj if m.r.success(j)];rows=[]
    for j in jj:
        for d,rec in m.r.attempts(j):
            rows.append(dict(id=j['id'],request_id=j['request_id'],backend_id=m.BACKEND,scientific_stage=j['stage'],attempt=int(d.name),body_sha256=j['body_sha256'],http_status=rec.get('http_status'),unknown=rec.get('outcome_unknown',False),elapsed_seconds=rec.get('elapsed_seconds'),request_sha256=c.sha(d/'request.json'),response_sha256=rec.get('response_sha256'),receipt_sha256=c.sha(d/'receipt.json') if (d/'receipt.json').exists() else None))
    state='R1_INFERENCE_DONE_WAIT_GPU_SHUTDOWN' if (O/'R1_INFERENCE_DONE.json').exists() else 'BENCHMARK_OR_FORMAL_IN_PROGRESS'
    c.putl(O/('request_ledger_complete.jsonl' if state.startswith('R1_INFERENCE_DONE') else 'request_ledger_benchmark.jsonl'),rows)
    if (O/'concurrency_benchmark.json').exists():
        b=c.read(O/'concurrency_benchmark.json');lines=['# AWQ-Marlin并发测试','', '|阶段|并发|HTTP200/请求|core有效|墙钟秒|请求/分钟|completion token/s|P90延迟秒|','|---|---:|---:|---:|---:|---:|---:|---:|'];flat=[]
        for s in b['stages']:
            lines.append(f"|{s['marlin_stage']}|{s['concurrency']}|{s['success']}/{s['requests']}|{s['core_valid']}|{s['wall_seconds']:.2f}|{s['requests_per_min']:.3f}|{s['completion_tokens_per_second']:.2f}|{s['latency_p90']:.2f}|")
            flat.append({k:v for k,v in s.items() if not isinstance(v,(dict,list))})
        lines+=['',f"选择并发：{b['selected_concurrency']}。规模只按新backend实测速度，加预定25%余量。",'',str(b['forecasts']), '', '085历史：360 HTTP200、0重试、串行中位25.289秒、最长41.984秒。来源outputs/085_r1_70b_valdemardi/formal_reconciliation.json；样本和输出长度不同，不要求耗时相同，不把速度差解释为能力差。','旧AWQ P0延迟377.016秒，824 completion tokens；新M0同输入同输出token数，延迟28.656秒。']
        c.write(O/'concurrency_benchmark.md','\n'.join(lines))
        fields=sorted(set().union(*(x.keys() for x in flat)))
        with (O/'concurrency_benchmark.csv').open('w',encoding='utf-8',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(flat)
    # Verify immutable scientific request bodies and samples without reading labels for scoring.
    old=c.lines(m.OLD_P/'jobs.jsonl');assert len(old)==len(jj)
    for a,b in zip(old,jj):assert a['id']==b['id'] and a['body']==b['body'] and a['request_id']!=b['request_id'] and b['backend_id']==m.BACKEND
    for name,h in c.read(m.OLD_O/'freeze.json')['files'].items():
        assert c.sha(m.OLD_O/name)==h
        if name!='request_manifest.jsonl':assert c.sha(O/name)==h
    assert len({j['request_id'] for j in jj})==len(jj)
    for j in done:assert c.read(m.r.success(j)/'receipt.json')['backend_id']==m.BACKEND
    health=c.lines(O/'service_health.jsonl');starts={tuple(x['process_start_time']) for x in health if x['process_start_time']}
    assert len(starts)==1,'Observed service restart needs separate reconciliation'
    check=dict(status='PASS',scope='runtime reconciliation and backend/sample isolation only; no scientific evaluation yet',independent_audit=False,HTTP200=len(done),backend_id=m.BACKEND,old_AWQ_used_for_formal=False,sample_freeze_changed=False,GT_accuracy_read=False,code_sha256={p.name:c.sha(p) for p in c.TASK.glob('marlin*096.py')},shared_runner_sha256=c.sha(c.TASK/'live_run096.py'))
    c.put(O/('runtime_selfcheck_complete.json' if state.startswith('R1_INFERENCE_DONE') else 'runtime_selfcheck_benchmark.json'),check)
    if state.startswith('R1_INFERENCE_DONE'):
        rec=c.read(O/'R1_INFERENCE_DONE.json');tier=c.read(O/'tier_selection.json');assert rec['HTTP200']==len(done)==len(tier['ids']);assert c.sha(O/'response_reconciliation.jsonl')==rec['reconciliation_sha256']
        reconciliation=c.lines(O/'response_reconciliation.jsonl')
        assert all(x['usage'] and type(x['usage']['prompt_tokens']) is int and type(x['usage']['completion_tokens']) is int for x in reconciliation)
        assert all(x['attempts']==1 for x in reconciliation)
        c.put(O/'cost_runtime_summary.json',dict(backend_id=m.BACKEND,cloud_API_calls=0,cloud_API_cost_cny=0,GPU_hourly_price_cny=None,GPU_total_bill_cny=None,billable_instance_start_unknown=True,new_backend_observed_span_seconds=rec['wall_seconds'],observed_span_cost_formula='wall_seconds / 3600 * user hourly price; does not include unobserved billed uptime',natural_coverage=800,natural_benchmark_reused=41,natural_new_formal=759,natural_formal_wall_seconds=c.read(O/'stage_natural.json')['wall_seconds'],natural_actual_new_requests_per_min=759/c.read(O/'stage_natural.json')['wall_seconds']*60,calibration_HTTP200=143,diagnostic_HTTP200=200,old_AWQ_diagnostic_success=1,old_AWQ_unknown_attempts=2,old_AWQ_excluded_from_formal=True,requests_never_repeated_within_backend=True,observed_service_process_start_unchanged=True))
        c.put(O/'GPU_shutdown_handoff.json',dict(status=state,backend='AWQ-Marlin',backend_id=m.BACKEND,Tier=tier['tier'],**{k:rec[k] for k in ['counts','HTTP200','core_valid','wall_seconds','concurrency','requests_per_min','prompt_tokens','completion_tokens','response_directory','reconciliation']},next_command='pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/marlin_offline096.py --gpu-shutdown-confirmed',GPU_price=None,GPU_rent=None,cloud_API_cost=0,fit_started=False,evaluation_started=False))
        c.write(O/'GPU_shutdown_handoff.md',f'''# R1_INFERENCE_DONE — 请关闭AutoDL

backend为AWQ-Marlin，Tier {tier['tier']}；正式{rec['HTTP200']}个HTTP200，core有效{rec['core_valid']}。校准/自然/诊断：{rec['counts']}。并发{rec['concurrency']}，推理跨度{rec['wall_seconds']/60:.2f}分钟，prompt/completion token {rec['prompt_tokens']}/{rec['completion_tokens']}。跨度含benchmark之间的本地间隔，不等于实例完整账单。

全部原始响应已本地保存并对账。现在可以关闭AutoDL实例；按最新用户指示，等待其确认关闭后再离线拟合PriorG、读取GT评价、bootstrap及报告。当前没有完成科学评价，也未升级默认。GPU小时价/完整租金未知，未伪报为0；新增token API0元。

恢复命令见MARLIN_README.md。旧AWQ仅诊断，不进入任何正式列；旧P1两个unknown不补跑。本次不为表格/报告继续发送GPU请求。
''')
    text=f'096当前使用独立AWQ-Marlin backend，状态{state}；旧AWQ全部隔离为部署诊断，样本与143校准监督不变。已保存新backend HTTP200 {len(done)}条；默认仍V4-B＋Frozen PriorG。'
    c.write(c.OUT/'CURRENT_STATUS.md',text+'\n\n最新入口：tasks/096_r1_native_priorg/MARLIN_README.md。旧READY_FOR_R1和live_v1为历史准备/旧AWQ快照。')
    for name in ['AGENTS.md','README.md','docs/PROJECT_STATUS.md']:
        path=c.ROOT/name;s=path.read_bytes().decode('utf-8');eol='\r\n' if '\r\n' in s else '\n';ll=s.splitlines()
        for i,line in enumerate(ll):
            if line.startswith(('096已按用户','- 096已按用户','096当前使用','- 096当前使用')):ll[i]=('- ' if line.startswith('- ') else '')+text+' [现场入口]('+('../' if name.startswith('docs/') else '')+'tasks/096_r1_native_priorg/MARLIN_README.md)。'
        s=eol.join(ll)+eol
        if name=='README.md':s=s.replace('没有自动续跑中的研究任务。','096正按用户新授权接续，状态见下方。')
        if name=='docs/PROJECT_STATUS.md':s=s.replace('没有自动进行中的下一研究任务。','096按用户新授权接续，当前执行状态见下方。')
        path.write_bytes(s.encode('utf-8'))
    path=c.ROOT/'docs/TASK_INDEX.md';s=path.read_bytes().decode('utf-8');s=s.replace('截至096零API准备','截至096 AWQ-Marlin执行');ll=s.splitlines();eol='\r\n' if '\r\n' in s else '\n'
    for i,line in enumerate(ll):
        if line.startswith('|096_r1_native_priorg|'):ll[i]='|096_r1_native_priorg|[AWQ-Marlin现场入口](../tasks/096_r1_native_priorg/MARLIN_README.md)|执行者运行核查；独立审计未执行|'+state+'，旧AWQ只诊断；正式评价待GPU关闭后离线执行|'
    path.write_bytes((eol.join(ll)+eol).encode('utf-8'))
    print(state,'HTTP200',len(done),flush=True)
if __name__=='__main__':main()
