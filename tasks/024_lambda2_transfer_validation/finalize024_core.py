"""Prepare final status and audit manifest after execution self-check, not independent audit."""
import importlib.metadata,json,subprocess,sys
from collections import Counter
import core024 as c
def run():
    a=c.OUT/'analysis_001';cost=c.read(a/'costs.json');decision=c.read(a/'decision.json');pairs=c.read(a/'paired.json')
    c.require(c.read(c.OUT/'verification_001/replay.json')['all_equal'],'Replay failed')
    c.require(c.read(c.OUT/'execution_closure.json')['remaining_unanswered']==[],'Unanswered requests')
    c.require(not (c.OUT/'live.lock').exists(),'Runner remains active')
    tests=c.read(c.OUT/'amendment_002/tests_before_evaluation.json');c.require(all(r['returncode']==0 for r in tests['results']),'Tests failed')
    # Save final integrity/arithmetic logs; no performance recomputation or APIs.
    logs=[]
    for name in ('verify024_core.py','check_results024.py'):
        r=subprocess.run([sys.executable,str(c.TASK/name)],cwd=c.ROOT,capture_output=True,text=True)
        logs.append(dict(script=name,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));c.require(r.returncode==0,'Final check failed: '+name)
    c.put(c.OUT/'verification_001/final_checks.json',dict(created_utc=c.now(),new_api_calls=0,results=logs))
    jobs=c.verify_inputs();attempts,term=c.load_attempts(jobs);byid={j['request_id']:j for j in jobs}
    boundary=c.read(c.OUT/'amendment_002/network_note_001.json')['created_utc'];phases=Counter();byarm={}
    for x in attempts:
        req=c.read(c.OUT/x['attempt_dir']/'request.json');phase='task_direct' if req['created_utc']>=boundary else 'system_proxy'
        phases[(phase,str(x['http_status']))]+=1
        j=byid[x['request_id']];key=j['model_key']+'/'+j['arm'];byarm[key]=byarm.get(key,0)+x['charge_cny']
    c.put(c.OUT/'verification_001/execution_diagnostics.json',dict(network_phase_counts={k+'/'+s:v for (k,s),v in phases.items()},occupied_cost_by_model_arm=byarm,attempt_distribution=dict(Counter(Counter(x['request_id'] for x in attempts).values())),per_model_arm={f'{m}/{arm}':dict(Counter(term[j['request_id']]['status'] for j in jobs if j['model_key']==m and j['arm']==arm)) for m in c.MODELS for arm in ('B','S')}))
    text='''# 024 当前状态：执行与自检完成，待独立审计

2026-09-19。完整020的10名已暴露development患者879条，冻结API-BGE C48不变。阿里云DeepSeek0731与Qwen3.8-27B各B/S一次，3516个HTTP200；3488正常有效、27带非核心格式异常有效、1个DeepSeek B核心verdict冲突无效。未重跑HTTP200；全部104次通信未知均保留并完成后续成功尝试。

- DeepSeek：U2−U0 +62/879，U2−B +37/878。
- Qwen：U2−U0 +23/879，U2−B +21/879。
- 两模型U2−U0的PA/MCC患者区间均正；U2−B的MCC区间均跨0。方向迁移支持，均未达预登记强迁移证据门槛。
- DeepSeek较U0新增false-S 27，Qwen新增9；类别代价保持。
- 总占用57.534444/80元＝usage原价估算50.876109＋未知预留6.658335，非账单。
- 28项测试、84项结果核对、15份核心机器文件离线重放字节一致。执行者自检不是独立审计PASS。
- 无新λ搜索、prompt/证据/BGE修改、reserved40调用或本地部署测试。本轮停止，不自动启动后续实验。

唯一主报告：[report.md](report.md)；[审计交接](audit_handoff.md)。用户amendment_002统一核心字段口径优先；旧协议、两次暂停和全部回执保留。
'''
    (c.OUT/'CURRENT_STATUS.md').write_text(text,encoding='utf-8',newline='\n')
    (c.TASK/'CURRENT_STATUS.md').write_text('''# 024 当前状态

执行、评价与执行者自检完成，待独立审计。见[正式状态](../../outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)与[唯一主报告](../../outputs/024_lambda2_transfer_validation/report.md)。不自动reserved40。

## 安全离线入口

- `python tasks/024_lambda2_transfer_validation/verify024_core.py`
- `python tasks/024_lambda2_transfer_validation/check_results024.py`
- `python tasks/024_lambda2_transfer_validation/analyze024_core.py --replay-dir outputs/replays/<new-directory>`

这些入口不加载密钥、不发送API；重放必须新建目录。core024.py为当前统一解析，analyze024_core.py为当前002有效交集评价。旧strict/repaired程序保留历史用途，不是当前主入口。收费runner不要用于重放；本次无剩余待调用工作。
''',encoding='utf-8',newline='\n')
    (c.OUT/'README.md').write_text('''# 024 成果入口

执行与自检完成，待独立审计。唯一必读[中文主报告](report.md) · [当前状态](CURRENT_STATUS.md) · [审计交接](audit_handoff.md)。

- 原[冻结协议](protocol_001.md)及[服务/价格/队列登记](preparation_001/registry.json)。
- 当前[执行期统一解析与配对评价修订](amendment_002/README.md)优先；旧无损修订/暂停记录均保留。
- [机器评价](analysis_001/metrics.json)、[配对及区间](analysis_001/paired.json)、[比较ID集合](analysis_001/comparison_cohorts.json)、[缺失记录](analysis_001/invalid_missing.json)。
- [正确数迁移](analysis_001/transitions.csv)、[患者结果](analysis_001/patients.csv)、[配对患者净变化](analysis_001/paired_patient_changes.json)。
- [累计费用](analysis_001/costs.json)、[执行收尾](execution_closure.json)、[离线重放](verification_001/replay.json)、[最终自检](verification_001/final_checks.json)。

不宣布独立审计PASS，不重新选择λ，不自动reserved40。API结果不是本地部署验证。
''',encoding='utf-8',newline='\n')
    audit='''# 024 独立审计交接

执行、正式评价及执行者自检完成；**待独立审计，执行者没有宣布审计PASS**。本次停止，不自动进入reserved40。

## 核心结论与分母

- DeepSeek U2−U0 +62/879、U2−B +37/878；Qwen +23/879、+21/879。
- 两模型同次S上的U2−U0 PA/MCC区间均正；相对普通B的MCC区间均跨0，均未达原强迁移证据门槛。
- 两模型新增false-S分别27/9。DeepSeek U2较历史020两轮少36/26条正确，不能继承历史绝对成绩。
- 1个DeepSeek B无效（verdict重复冲突），其S合法；不得把878分母的主描述表差值误当879的U2−U0。其ID为1e492144-2240-96c8-3ac4-ddd46dd22fca，request_id=511697dd941909be500dad6a。

## 必审材料

1. preparation_001/manifest.json、jobs.jsonl、cohort.csv：879冻结claim、同一API-BGE C48、同019prompt；body仅model更换。未新BGE、未reserved40。
2. protocol_001.md是原始协议；amendment_001是首次相同键无损修复；**amendment_002/README.md是用户后续明确授权且性能评价前登记的当前口径**。不能用旧“任意重复键停发/全合法才评价”判断本轮后续执行越权。
3. core024.py统一解析所有旧/新response，reason/checks异常只记diagnostic；不同值核心冲突invalid，HTTP200绝不重跑。原response、原严格解析状态和旧暂停均保留。27条valid_with_format_anomaly不是新增医生gold。
4. attempts全量3620次request/receipt：3516个HTTP200、104次通信未知；每个HTTP200唯一。未知预留6.658335不释放；usage峰时原价估算50.876109，总57.534444/80元。不是账单。
5. 曾出现代理路径断连；任务进程直连同一endpoint后续跑。未改OS代理、模型、prompt/证据；传输等价测试和源码指纹见amendment_002。network计数见verification_001/execution_diagnostics.json，不把时序改善说成严格网络因果证明。
6. analysis_001：每比较各自paired complete-case、完整/排除ID、n和hash；直接模型比较取共同有效集合。missing-as-error仅PA，不补三分类预测。002实现未改、1000患者cluster bootstrap、λ只0/2。
7. report.md为唯一主报告；CURRENT_STATUS、导航只同步现行状态。019–023报告/结果未改，旧024报告见status_history/paused_001和paused_002。

## 自检证据

- amendment_002/tests_before_evaluation.json：9个测试脚本共28项通过，含隔离临时目录的合成端到端评价；该合成数据不属于研究结果。
- verification_001/final_checks.json：3516 frozen body逐条重建、旧checkpoint/修订/请求回执hash、预算预留、3490条旧严格合法回答core不变；84项混淆矩阵/有效交集/净正确/false-S守恒核对。
- verification_001/replay.json：15份正式核心机器输出在outputs/replays/024_final_self_replay_001独立新目录重放，逐字节相同；该目录按已有.gitignore排除，可随时重建。没有改.gitignore。
- 正式分析manifest及最终交审manifest保留代码/输入/回执/成果指纹。HEAD和未提交状态在handoff.json；当前任务未提交/推送。

## 安全重放

```
python tasks/024_lambda2_transfer_validation/verify024_core.py
python tasks/024_lambda2_transfer_validation/check_results024.py
python tasks/024_lambda2_transfer_validation/analyze024_core.py --replay-dir outputs/replays/<new-directory>
```

禁止用run024*.py做离线复查；那些是真实收费入口。重放不覆盖历史目录。report中的paired_patient_changes.json为确定性派生补表，由report024_core.py生成，最终交审manifest另行绑定。

## 后续边界

此次只有跨服务/模型开发材料验证。Qwen不等于本地部署；分数不是校准医学概率；原解释不随U2改判重写；服务条件、非同期和单轮局限保持。是否冻结最终Judge并进入reserved40须独立审计后另行决定，本执行不启动后续工作。
'''
    (c.OUT/'audit_handoff.md').write_text(audit,encoding='utf-8',newline='\n')
    from current_navigation024 import run as navigation
    navigation(True)
    env=dict(python=sys.version,executable=sys.executable,packages={n:importlib.metadata.version(n) for n in ('numpy','pandas','scipy','scikit-learn')})
    c.put(c.OUT/'verification_001/environment.json',env)
    # Explicitly restrict credential scan and fingerprint inventory to024 artifacts/current navigation.
    paths=[p for folder in (c.TASK,c.OUT) for p in folder.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    key=c.load_config(c.ROOT/'.env.aliyun').api_key
    c.require(bool(key),'No local key for secret-exposure check')
    for p in paths:c.require(key.encode() not in p.read_bytes(),'Credential in artifact; do not publish')
    nav=[c.ROOT/p for p in ('README.md','AGENTS.md','docs/PROJECT_STATUS.md','docs/REPRODUCIBILITY.md')]
    c.put(c.OUT/'handoff.json',dict(created_utc=c.now(),independent_audit=False,git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip(),git_status=subprocess.check_output(['git','status','--short'],cwd=c.ROOT,text=True),sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in paths},current_navigation_sha256={p.relative_to(c.ROOT).as_posix():c.file_hash(p) for p in nav},credential_scan_pass=True,original_results_019_023_unchanged=True))
    print(c.canonical(dict(status='execution_complete_pending_independent_audit',cost_cny=cost['total_occupied_cny'],fingerprinted_files=len(paths))))
if __name__=='__main__':run()
