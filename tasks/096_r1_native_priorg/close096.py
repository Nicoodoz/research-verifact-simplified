"""Final documents/navigation; no service access and no new research."""
from pathlib import Path
import common096 as c
BACKEND='valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k';O=c.OUT/BACKEND
def replace_file(path,fn):
    data=path.read_bytes();s=data.decode('utf-8');end='\r\n' if '\r\n' in s else '\n';s=fn(s);path.write_bytes(s.replace('\r\n','\n').replace('\n',end).encode('utf-8'))
def main():
    assert c.read(O/'selfcheck.json')['status']=='PASS' and c.read(O/'public_replay_verification.json')['status']=='PASS'
    c.put(O/'shutdown_confirmation.json',dict(status='USER_CONFIRMED_AUTODL_POWERED_OFF',source='User: autodl已关机，你继续',confirmation_preceded_R1_fit_and_evaluation=True,post_shutdown_endpoint_requests=0,provider_power_state_not_independently_probed=True))
    sourcefiles=[(c.ROOT/'docs/01_codex_execution_prompt.md','00_offline_user_prompt.md'),(Path('C:/Users/13359/.codex/attachments/a6970812-bd0e-48bb-8786-bb8af45d8306/已粘贴的文本.txt'),'01_live_user_prompt.md'),(Path('C:/Users/13359/.codex/attachments/dea802ac-e494-4a2d-9d84-e3071a5abd2b/已粘贴的文本.txt'),'02_marlin_user_prompt.md')]
    manifest=[]
    for source,name in sourcefiles:
        dest=c.TASK/'protocols'/name;dest.parent.mkdir(parents=True,exist_ok=True);text=source.read_text(encoding='utf-8-sig')
        if not dest.exists():dest.write_text(text,encoding='utf-8',newline='\n')
        manifest.append(dict(archive=name,source_sha256=c.sha(source),archive_sha256=c.sha(dest),note='task-only authorized user protocol; source user-owned file not staged; UTF8 no BOM archive'))
    c.put(c.TASK/'protocols/source_manifest.json',manifest)
    status='096已完成AWQ-Marlin跨Judge与PriorG迁移验证：自然800条Original/V4 raw/R1 raw正确657/617/599；R1重新适配595，旧PriorG直接迁移616且与prior-only同标签。共同798条当前V4＋G正确664、MCC0.5802，R1-adapted594/0.4163。停止本轮适配，默认不变；1143 HTTP200、0重试，AutoDL用户已关机，按token新API0元、GPU租金未知。自检通过，独立审计未执行。'
    def entry(s,prefix):
        lines=s.splitlines()
        for i,line in enumerate(lines):
            if line.startswith(('096当前使用','- 096当前使用','096已按用户','- 096已按用户')):lines[i]=('- ' if line.startswith('- ') else '')+status+f' [正式报告]({prefix}outputs/096_r1_native_priorg/report.md) · [论文更新]({prefix}outputs/096_r1_native_priorg/manuscript_implications.md)。'
        return '\n'.join(lines)+'\n'
    replace_file(c.ROOT/'AGENTS.md',lambda s:entry(s,'').replace('095结项后','096结项后'))
    replace_file(c.ROOT/'README.md',lambda s:entry(s,'').replace('**095（2026-09-28）**','**096（2026-09-28）**').replace('096正按用户新授权接续，状态见下方。','096已结项，不自动启动下一任务。'))
    def project(s):
        s=entry(s,'../').replace('2026-09-28，095完成','2026-09-28，096完成').replace('当前研究已完成至095；本轮起始HEAD 5ec748edd63be29d35fa920f10874aa158501ae5','当前研究已完成至096；096起始HEAD 28daf95e9b12270d8089246176023c66c4cf298e').replace('096按用户新授权接续，当前执行状态见下方。','096已完成，不自动启动下一任务。')
        s=s.replace('|095统一基准/最小差异|','|096跨Judge/PriorG迁移|自然800、诊断200；143校准中142有效，R1 G到−6下界|R1 raw与重新适配均未形成综合优势；默认V4＋G不变，AutoDL用户已关机|\n|095统一基准/最小差异|')
        s=s.replace('没有本轮授权下的新服务访问或下载。','096已在用户授权的AWQ-Marlin服务完成1143次请求，用户确认关机后全部离线分析；旧AWQ结果仅诊断，无新权重下载。')
        return s
    replace_file(c.ROOT/'docs/PROJECT_STATUS.md',project)
    def index(s):
        s=s.replace('截至096 AWQ-Marlin执行','截至096结项');lines=s.splitlines()
        for i,line in enumerate(lines):
            if line.startswith('|096_r1_native_priorg|'):lines[i]='|096_r1_native_priorg|[正式报告](../outputs/096_r1_native_priorg/report.md) · [论文更新](../outputs/096_r1_native_priorg/manuscript_implications.md)|[执行者自检](../outputs/096_r1_native_priorg/'+BACKEND+'/selfcheck.json)，独立审计未执行|AWQ-Marlin1143 HTTP200；自然R1 raw599/800，适配595；停止适配、默认不变，不自动097|'
        return '\n'.join(lines)+'\n'
    replace_file(c.ROOT/'docs/TASK_INDEX.md',index)
    def policy(s):
        lines=s.splitlines()
        for i,line in enumerate(lines):
            if line.startswith('096最新用户已授权'):lines[i]='096已完成：AWQ-Marlin1143个HTTP200、0重试；旧AWQ1成功＋2未知仅部署诊断，全部保留。用户确认AutoDL已关机，拟合/评价离线完成。新增按token收费API0次/0元，GPU小时价/完整账单未知；不继承095额度、不把API上限套成租金。结果与费用见[096报告](../outputs/096_r1_native_priorg/report.md)，不自动新实验。'
        return '\n'.join(lines)+'\n'
    replace_file(c.ROOT/'docs/API_POLICY.md',policy)
    replace_file(c.ROOT/'docs/RESEARCH_EXECUTION.md',lambda s:s.replace('当前095已完成','当前096已完成'))
    c.write(c.OUT/'CURRENT_STATUS.md',status+'\n\n当前正式结果仅在'+BACKEND+'；旧READY_FOR_R1、live_v1与GPU_shutdown_handoff是保留的阶段快照。最新入口report.md；不自动恢复推理。')
    c.write(c.TASK/'README.md',f'''# 096已结项：R1原生比较与PriorG同配方适配

[中文报告](../../outputs/096_r1_native_priorg/report.md) · [论文更新](../../outputs/096_r1_native_priorg/manuscript_implications.md) · [正式数据](../../outputs/096_r1_native_priorg/{BACKEND})。

自然800条Original/V4 raw/R1 raw正确657/617/599；旧PriorG迁移616、重新适配595。R1评分极端化、NA识别弱，重新适配未形成综合收益。默认V4-B＋Frozen PriorG不变，不继续搜索、不自动下一任务。旧AWQ仅诊断；用户已确认AutoDL关闭。

## 当前复现入口（全离线，不需GPU）

公开标签、分数和预测足以重放主指标、患者配对区间及R1校准参数：

```powershell
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/public_replay096.py
```

本地保有私有原生回执时，可重放全部源核对和分析（不会发送请求）：

```powershell
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/marlin_offline096.py --gpu-shutdown-confirmed
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/diagnostics096.py
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/supplement096.py
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/selfcheck_final096.py
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/report096.py
```

现有冻结JSON拒绝不同内容覆盖。若代码/环境改变导致重放不同，应另存核查结果，不能删除旧输出强行覆盖。selfcheck.json是执行者自检；其中代码哈希是当时验证快照，最终完整文件哈希见final_artifact_manifest_v2.json。当前运行无须再执行prepare、benchmark、formal或访问端点。

## 历史执行与授权

protocols/归档用户零API、现场和Marlin三版任务要求，较新者优先。旧control096/runner096及READY_FOR_R1是零API准备快照；LIVE_README与live_v1是旧AWQ诊断阶段；MARLIN_README保留现场命令，但用户已关机，不自动恢复服务。

science freeze继承live_v1：7484合格母体，800/600/400嵌套自然面板；Marlin仅换backend身份和请求缓存key。原051计划143校准/16患者，1个length后实际142交集。R1 theta=-6的原052无约束success=False保留，新增KKT核验确认原范围边界最优，不扩范围或搜索新配方。三次工程更正在正式输出目录登记。

临床请求/原始回执保存在.local_models/096_r1_native_priorg/，不推送；公开仅ID/标签/分数/哈希/指标。原作者桥接复用078，不新收费调用；GPU租金未知，不伪造为0。
''')
    c.put(O/'closure.json',dict(status='COMPLETE_NO_DEFAULT_UPGRADE',utc=c.now(),GPU_shutdown_user_confirmed=True,new_inference_after_shutdown=0,next_task_started=False,default_unchanged=True,independent_audit=False,report='outputs/096_r1_native_priorg/report.md'))
    print('NAVIGATION_CLOSED')
if __name__=='__main__':main()
