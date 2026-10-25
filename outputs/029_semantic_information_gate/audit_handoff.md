# 029 独立审计交接

## 状态及结论边界

run_001已完成：12条件×患者OOF、025→026、026→025，共36组。首次用户只要求冻结和无人值守启动；本次“完成的话对029收尾”授权后新增报告与收尾核验，未重新实验。**执行者自检通过，独立审计待进行。**

主要判断：D-Logistic联合信息在统一OOF中相对A/B同风险混合包络+11/+9R，条件患者区间全正，保留该正信号；但反向迁移保留率71.1%，相对A/B同风险−0.5/0R，尚不稳定。单独trace较弱，XGBoost未提供可靠补救。不是“完全无信息”，也不能称正式方法成立或产生新winner。停止本轮，不追加特征、分类器、阈值、030或reserved40。

## 审计优先项

1. **冻结时序。** preparation_001/manifest早于首个正式拟合，哈希包含源码、config、feature schema、原来源和环境。仅新增close029.py/收尾文档，不修改事前程序或run_001。git HEAD为29ad471045829e79546c9a58b75f2ecaa2aff34f，最终工作区及指纹见handoff_001.json。
2. **真实分母。** 全1529条、16名development患者；103+52=155候选，只有15名患者有候选。15057保留于16折及完整评价，不能悄悄丢弃。003分组仅用于患者ID边界检查，不读reserved病例。
3. **公平主比较。** A也在029重新训练；A/B/C/D×Logistic/XGBoost共8主条件，C/D去质量另4条件，无其他搜索。S+D复用025精确定义；repeat3维、trace关系6维/质量3维；没有患者/作者/队列/GT/自由文本/人工类型输入。历史SD仅参照，不能代替A。
4. **患者隔离。** 16外层LOPO，每折内层训练患者LOPO，取训练R概率80%分位对应的最严格阈值。每折保存全部内外ID、scaler和模型、概率及阈值；测试GT不进入训练/阈值。无候选患者仍有记录。迁移完全排除对侧患者。实际没有触发单类/空训练fallback，预设逻辑及合成测试仍保留。
5. **固定模型。** StandardScaler+L2 Logistic C0.1；独立环境sklearn1.9.1用l1_ratio=0表达L2。XGBoost固定40棵、depth2、min_child_weight5、L2=5/L1=1，全采样，不早停、不使用测试eval_set；没有搜索。不同环境不应强求025原概率逐位相同，029内部比较环境一致。
6. **评价。** 002 evaluate/paired_compare、完整队列、候选拒绝退U0。R/H/W、risk=H+W、net=R−H分开。全非负global状态直到全S及确定性/随机混合参考均保存，不缩到λ2。参考的GT知情包络只作描述，不是新阈值或可部署性能。
7. **不确定性。** 1000次患者cluster bootstrap，字典序患者、RandomState0..999，与002一致；只重抽固定OOF/迁移输出，不重新训练。不能把条件区间当完整训练泛化保证或据多条件最佳单点选winner。
8. **冲突与质量消融。** 复用027既有59例冲突，不在该子集选模型。改善主要在026，025未重复。C/D-XGBoost去质量后全部三个scope的正式概率/阈值/预测均相同；D-Logistic去质量仍保留增量，不应将全部收益归因格式代理，也不据消融换winner。
9. **费用和环境。** 0 API、0费用。使用research-verifact-029，未安装/升级原research-verifact依赖。不读.env，不初始化收费client；runner禁socket连接。数据和历史001–028、.gitignore、API_POLICY均未改。

## 已做的执行者检查

`closeout_001`：64,110项通过；直接从保存的coef/scaler或XGBoost booster JSON重算3096个内外模型状态的概率，0次拟合。核对精确训练/测试集合、训练内阈值、最终预测合并、全部指标/混淆矩阵和RHW守恒，独立LP核验全部正式matched工作点。重检run_001及各evaluation全部内容指纹。启动前8项合成测试，包括测试GT改变不影响结果、单类边界及合成全评价。

`close029.py`是事后只读自检，不属于事前训练配置，也不是独立审计。其最后一项要求tracked工作区无变化：本次在同步导航前执行，因此通过；若当前四份导航仍有未提交修改，此辅助脚本会在末尾拒绝。先人工审阅导航差异，或在对应干净审计副本运行；不要为通过检查丢弃用户修改。该限制不影响下述正式离线重放入口。

## 安全复查与重放

使用已有独立029环境，输出必须为新的run-id；不运行prepare029.py或launch029.ps1覆盖正式目录。

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -B -m unittest discover -s tasks/029_semantic_information_gate -p test029.py -v
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/029_semantic_information_gate/run029.py --run-id audit_replay_001
```

完整重放会离线重新拟合固定模型并完成全部统计，运行数分钟；不会访问API，不覆盖run_001。日期/路径/进程ID等运行元信息不要求逐字节一致，应对齐各条件predictions及evaluation内容。本轮收尾未重复完整训练，而是复核已保存模型和预测。

只读模型核查（tracked工作区干净时）：

```powershell
E:/miniconda3/envs/research-verifact-029/python.exe -B tasks/029_semantic_information_gate/close029.py outputs/029_semantic_information_gate/audit_closeout_001
```

## 导航与停止

新增中文report、CURRENT_STATUS、closeout与本交接，并只追加四份现行导航。run_001、preparation_001和原stdout/stderr保持字节。自动运行时RUN_STATUS中的“未写正式结论”是当时快照，最新状态以本报告/CURRENT_STATUS为准。不宣布独立审计PASS，不自动commit/push。
