"""Close CPU preparation and record the user's actual5090 handoff; no GPU run."""
from pathlib import Path
import ast
import subprocess
import common107 as c

NAV=('AGENTS.md','README.md','docs/PROJECT_STATUS.md','docs/RESEARCH_EXECUTION.md','docs/RUN_ENVIRONMENT.md','docs/TASK_INDEX.md')
BASE='bd4cc3e3a35ed3e1a98b115c1e14c02759da895d'

def main():
    data=c.read(c.OUT/'data_checks.json');cpu=c.read(c.OUT/'cpu_checks.json');tiny=c.read(c.OUT/'torch_cpu_tests.json')
    pkg=c.read(c.OUT/'implementation_package.json');check=c.read(c.OUT/'implementation_package_checks.json')
    assets=c.read(c.OUT/'5090_assets_verification.json')
    assert data['status']=='PASS' and cpu['passed'] and tiny['passed'] and check['status']=='PASS'
    assert assets['all_model_SHA_match'] and assets['all_environment_versions_match']
    assert pkg['manifest_sha256']==check['manifest_sha256'] and pkg['archive_sha256']==check['archive_sha256']
    assert not tiny['cuda_initialized'] and not cpu['torch_imported']
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=c.ROOT,text=True).strip()==BASE
    status='CPU_PREPARATION_COMPLETE_5090_HANDOFF_RECEIVED'
    summary=('107阶段一CPU准备完成，用户已交接RTX5090 32GB（2.88元/小时，20:40起计费），不再等待租卡。'
        '两臂label_only/support_aux从原9B新训同196×2轮/50步，唯一差异为训练期prompt末端S/non-S BCE权重1；'
        '保留105主loss、原prompt/JSON/parser与评价500，按新授权检查评价batch2、必要时1，两臂同分组。'
        'CPU因果LoRA梯度/恢复、数据/预算/包核验通过；新机原9B全SHA及固定环境通过，100GiB数据盘几乎全空。'
        '阶段一推送后直接做5090真实最长backward/内核/显存/吞吐及整轮20元门槛，通过即执行。API0；当前无107分类结果，不启动108/升级默认。')
    c.write(c.OUT/'preparation_report.md',f'''# 107阶段一准备及实际5090接续

**{status}。** 已完成CPU实现与私有最小包，用户已提供开机RTX5090 32GB、2.88元/小时，计费从2026-10-28北京时间20:40累计，包含等待。阶段一双仓库推送后直接进入该实例工程检查，不再停在旧租卡交接点。

|项目|核验结果|
|---|---|
|训练输入|原104/105的196条逐字节相同，S83/NS62/NA51；辅助GT为83正/113负；GT/reference/claim不改|
|公平设计|两臂从原9B相同LoRA重新初始化，同顺序、2轮50步/392消费，原105分段mean CE与尾批4归一不变；不采用106 sum/512方案|
|辅助监督|单次backbone前向读取答案前prompt末态，线性头FP32 BCE权重1；局部seed103028不消耗共享RNG；梯度进入LoRA，head参与优化/裁剪/完整恢复|
|推理与范围|原JSON/parser、greedy/thinking off/完整输入/384上限；辅助头不用于推理；训练40与选型20隔离，固定自然400/压力100，确认40人不新增使用|
|真实tokenizer|196主loss映射与500输入SHA同105；新107按用户授权重排为batch2的250组，两臂一致；旧105批次不改|
|CPU验证|{cpu['tests_run']}项数据/预算/分析测试与{tiny['tests_run']}项tiny因果attention+LoRA张量测试通过；真实主loss值/梯度等价、答案独立、辅助梯度、fresh初始化、两槽恢复、Adam/scheduler/RNG及断写保护|
|私有运行包|{check['manifest_files_verified']}个manifest文件及归档SHA通过，空目录/PYTHONPATH清空后的import/help通过，未加载9B或初始化CUDA；包不含基础/适配器权重和凭据|
|新实例|RTX5090总32607MiB；原9B四分片及所有小文件SHA通过，11项关键环境版本与105相同，Python3.12.3；数据盘100GiB几乎全空，无需下载/重装/扩容|

辅助目标为L=L105+BCEWithLogits(w·h[prompt_tokens−1]+b,1[GT=S])。标准LoRA_B=0初始时A首步梯度可为0，CPU已验证B从首步、A更新后接收辅助梯度。头在外层BF16 autocast下仍以FP32计算。完整teacher forcing序列复用要求因果前缀不依赖未来答案，CPU已测，真实9B仍须实测。推理不调用辅助头，不投票或后处理。

本次5090接续只新增必要工程适配：BF16、micro1、完整输入和训练目标不改；原batch8曾约38.5GB不能用于32GB，优先实测batch2，若必须1则先同步107配置/包/校验并在正式评价前冻结。两臂均在本次5090新训/新评，A800成绩只作历史参照。现有镜像文件可用不等于5090内核兼容或最长backward可运行。

**尚未执行真实9B/GPU方法验证，也没有107分类指标。** 下一步实测内核、最长完整训练样本backward（含Adam驻留）、辅助梯度、显存余量、因果前缀、恢复连续下一步及实际吞吐。技术探针更新不进入正式初始化。实测预算采用5090当前卡的训练/保存/prefill/decode速度，覆盖两臂完整训练及各500条评价、已发生计费与关机余量；不套A800 batch8速度。超过20元或无法保持条件时报告缺口/阻塞，不改量化、输入或方法。API固定0。

历史A800时间只能作算术情景：76–109分钟按当前2.88元/小时并另预留2元约5.65–7.25元，120分钟约7.76元；**不是5090实测耗时预测**。本次18元运营线相当于375分钟，20元为416.67分钟，均从20:40开始累计。缺件或兼容性修复若需要长时间处理，及时报告预计耗时费用并建议先关机。停止进程不等于停GPU计费。

私有包`{Path(pkg['archive']).name}`，{pkg['archive_bytes']:,} bytes；manifest SHA256 `{pkg['manifest_sha256']}`，详见[包回执](implementation_package.json)。临床训练/评价原文、完整回执、凭据、权重、检查点与缓存均不上传GitHub。公开结果是准备证据，不是方法有效性。子代理分工/交叉检查不是独立审计。

GPU结束后保存适配器、辅助头、必要完整检查点和原始回执并通知用户关机，确认停计费后CPU分析。重新计算本次两臂共同有效ID，自然/压力分报MCC/PA/false-S、三类召回和混淆、救回/误伤、错误放行新增/避免、患者配对区间及成本。不能用减少S掩盖正确S/NS/NA损失；paper_r1仅历史参照。结果好坏均如实报告，不在500条调权重/采样/阈值/轮数，不用后续40人、不启动108或升级默认。

[冻结协议](../../tasks/107_support_aux/protocol.md) · [实际接续](../../tasks/107_support_aux/GPU_HANDOFF.md) · [资源摘要](resource_readiness.json) · [CPU检查](cpu_checks.json) · [真实张量CPU检查](torch_cpu_tests.json) · [实例权重环境](5090_assets_verification.json)。

主仓库准备起点为`{BASE}`，原105/106成果与冻结工件不改。阶段一CPU工作新增收费API0、未运行GPU计算；用户实例已开机产生的本次GPU费用从20:40起进入107累计账本，不能写作本次GPU总费用0。实际发布以Git提交记录为准。
''')
    for name in NAV:
        path=c.ROOT/name;raw=path.read_bytes();bom=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
        text=raw[len(bom):].decode('utf-8');nl='\r\n' if '\r\n' in text else '\n';text=text.replace('\r\n','\n')
        lines=text.split('\n')
        if name in NAV[:4]:
            assert lines[2].startswith('106研究')
            pre='' if name in NAV[:2] else '../'
            lines[2]=summary+f' [107准备报告]({pre}outputs/107_support_aux/preparation_report.md) · [107接续]({pre}tasks/107_support_aux/GPU_HANDOFF.md)。'
            text='\n'.join(lines)
        if name=='AGENTS.md':
            text=text.replace('## 当前状态与数据授权\n\n','## 当前状态与数据授权\n\n- 107用户已交接5090 32GB、2.88元/小时、本次20:40起计费；阶段一推送后直接工程检查，技术和整轮20元/API0门槛通过即执行两臂fresh训练/各500评价。允许评价batch2必要1、正式前冻结两臂同分组，不改BF16/micro1/完整输入；不使用确认40人。\n')
        elif name=='docs/PROJECT_STATUS.md':
            text=text.replace('106准备完成，待GPU决策','107 CPU准备完成，5090接续已提供',1)
            text=text.replace('|106标签目标准备|','|107支持性辅助监督|原196两臂fresh、辅助BCE、CPU验证及最小包完成；新5090权重/环境/磁盘通过|已交接32GB5090@2.88/h，20:40计费；推送后直接GPU工程检查，整轮20元/API0门槛通过执行|\n|106标签目标准备|',1)
        elif name=='docs/RESEARCH_EXECUTION.md':
            old=next(l for l in text.split('\n') if l.startswith('105已完成且用户确认关机'))
            text=text.replace(old,'105已完成且用户确认关机，不自行恢复旧实例。106保留为历史CPU准备，其mean/sum建议不进入107。用户已明确交办107并交接新5090 32GB（2.88元/小时，20:40计费）：阶段一推送后直接做实际工程检查，技术与整轮GPU20元/API0门槛通过即训练评价，无需再次批准普通步骤。按新授权评价batch2必要1，正式前两臂冻结同分组；BF16/micro1/完整输入与方法不改。GPU停计费后CPU分析，各阶段推送两仓库，不用确认40人/不启动108/不升级默认。')
        elif name=='docs/RUN_ENVIRONMENT.md':
            lines=text.split('\n');lines[0]='# 当前环境与启动方式（2026-10-28核对）'
            lines[2]='107 CPU数据/统计/评价/包核验继续用research-verifact-029；tokenizer及tiny因果LoRA CPU复用research激活加032 venv，未加载9B/初始化CUDA，无安装升级。用户已交接5090 32GB，新机/root/verifact_image原9B全部SHA与11关键依赖通过，数据盘100GiB几乎全空。阶段一推送后直接实测5090内核/最长backward/显存及吞吐，不能以105峰值代替；评价batch2必要1，正式前同分组冻结。[107交接](../tasks/107_support_aux/GPU_HANDOFF.md)。'
            text='\n'.join(lines)
        elif name=='docs/TASK_INDEX.md':
            text=text.replace('106准备完成，待GPU决策','107准备完成，5090接续已提供',1)
            text=text.replace('|106_label_preparation|','|107_support_aux|[准备报告](../outputs/107_support_aux/preparation_report.md) · [协议](../tasks/107_support_aux/protocol.md) · [接续](../tasks/107_support_aux/GPU_HANDOFF.md)|[执行者自检](../outputs/107_support_aux/final_selfcheck.json)，非独立审计|CPU准备完成，新5090已交接；推送后技术/整轮20元预算通过即执行；API0|\n|106_label_preparation|',1)
        path.write_bytes(bom+text.replace('\n',nl).encode('utf-8'))
    c.put(c.OUT/'final_selfcheck.json',dict(task=107,status=status,executor_checks_only=True,independent_audit=False,
        implementation_preparation_pass=True,method_effectiveness_proven=False,CPU_tests=cpu['tests_run'],tiny_tests=tiny['tests_run'],
        original196_and105_main_loss_preserved=True,both_fresh_arms=True,confirmation40_new_use=False,
        current_instance_assets_SHA_environment_verified=True,current_5090_GPU_model_checks_executed=False,
        user_rented_instance_handoff_received=True,waiting_user_rental=False,actual_GPU_billing_active=True,
        billing_start_beijing='2026-10-28 20:40',hourly_cny=2.88,GPU_cap_cny=20,API_cny=0,
        package_manifest_sha256=pkg['manifest_sha256'],publication_authorized=True,
        publication_status_at_formation='PENDING_DUAL_REPOSITORY_COMMIT_PUSH',source_main_head=BASE))
    public={p.relative_to(c.ROOT).as_posix():c.sha(p) for folder in (c.TASK,c.OUT) for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    public.update({p:c.sha(c.ROOT/p) for p in NAV})
    private={p.relative_to(c.ROOT).as_posix():c.sha(p) for p in [c.PRIVATE/'train/label_only.jsonl',c.PRIVATE/'train/support_aux.jsonl',c.PRIVATE/'eval_inputs.jsonl',Path(pkg['bundle'])/'manifest.json',Path(pkg['archive'])]}
    c.put(c.OUT/'preparation_freeze.json',dict(task=107,stage='CPU_PREPARATION_5090_HANDOFF',formed_at=c.utc(),files=public,
        private_files=private,source_main_head=BASE,old105_106_freezes_not_modified=True,
        user_authorized_runtime_amendment='RTX5090 BF16 unchanged; eval batch2 or1 before formal evaluation',
        verification_scope='full stage snapshot; historical replay uses this stage commit; simplified omits intermediates'))
    print(c.canonical(dict(status=status,public_files=len(public),private_fingerprints=len(private))))

if __name__=='__main__':main()
