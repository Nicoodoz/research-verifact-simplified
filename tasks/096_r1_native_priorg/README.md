# 096已结项：R1原生比较与PriorG同配方适配

[中文报告](../../outputs/096_r1_native_priorg/report.md) · [论文更新](../../outputs/096_r1_native_priorg/manuscript_implications.md) · [正式数据](../../outputs/096_r1_native_priorg/valdemardi_r1_70b_awq_marlin_vllm0101_fp16_20k)。

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
