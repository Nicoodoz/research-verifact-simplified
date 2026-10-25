# 019–021联合独立审计证据（2026-09-19）

结论：[019](../../019_support_boundary_screen.md) · [020](../../020_lambda2_patient_validation.md) · [021](../../021_bge_localization.md)。

- audited_files_sha256.json：审前独立记录的7557个019–021源码／输出文件指纹；同步后原文件仍全部匹配。新增CURRENT_STATUS不回写原协议、报告或handoff。
- raw_audit.py / raw_summary.json：独立标准库解析019/020全部原始回执与费用；乘法形式验证8066个离线解码标签，没有导入执行者解析或解码函数。运行时从仓库根目录传入一个新输出JSON路径。
- replay019/020/021_summary.json：通过新安全入口实际重放后的22/11/6个文件一致结果；019决定仅忽略生成时间。完整生成材料在被忽略的outputs/replays，非第二套正式成果。
- run_tests.py / tests.log：265项既有与019/020测试，全部断网通过；新增tests/test_completed_replay.py的4项保护测试另行通过，合计269项。测试没有真实付费API。
- local_check.py / local_environment_check.json：本机两权重哈希、全部49246个pair无截断长度和实际环境版本。本次未重跑GPU、不新建空环境；脚本保留当时TEMP输出目录，另行复跑时指定新输出位置。
- bindings_check.json：审前历史清单、authority与021 manifest核对。18522/21383历史条目仅允许的当前导航已变化；计算源码绑定无漂移。
- state_sync.json：用户授权后的当前文档／环境／忽略配置同步范围；历史字节保持，不伪装成实验运行前状态。
- manifest.json：本证据及新增审计记录的指纹。

日常复查使用[安全入口](../../../docs/REPRODUCIBILITY.md)。本次是快速执行／统计／复现审计，不新增医学GT，不将执行者语义深读数量当作本次独立深读。源模型页面受限的核查范围、GPU与环境安装未重跑等限制见021审计。
