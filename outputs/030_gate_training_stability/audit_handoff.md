# 030 独立审计交接

## 范围与状态

执行及执行者收尾完成，**不宣称独立审计PASS**。正式输入为preparation_001，正式实验run_001，收尾核验closeout_001。初次授权只准备/启动；本次用户明确要求“报告什么的”收尾后新增report、自检及导航，未改原run或事前方案。

被继承HEAD：49dc22a6（029独立审计提交；完整HEAD、工作区及最终hash见handoff_001.json）。未commit/push。0API，0费用；原research-verifact环境、API_POLICY、.gitignore和001–029均保持。没有访问reserved病例或新增医学标注。

## 优先审查

1. **不是新Gate开发。** 仅A/B/D，features/config/learning029直接沿用029冻结条件；Logistic、标准化、λ2、80%训练内R阈值未改。新代码只改变患者训练集合并评价稳定性，不运行XGBoost/C/质量消融，不按结果挑组合。
2. **规模与测试分母。** 15有候选患者逐一held-out，k=3/5/8/11/14从其余14人选择。每轮汇总15个患者外模型并补无候选15057，全部为同1529条完整测试记录；不能误读为一个11人模型在16人上测试。155候选身份不变。
3. **GT盲组合与重复。** SHA256 seed/rep/held/training ID事前确定，同rep内规模嵌套。5人来源025/026=4/1、3/2、1/4，全部可行且共用测试患者。160安排中19个k14重复作alias，141个不同完整轮次；1,452个训练集合×3方法=4,356个最终模型。重复切分不是新增独立样本。
4. **真实重训与缓存。** 每个不同集合内层LOPO定阈值，再全子集拟合；相同集合的确定性模型缓存跨held使用。所有训练/内层/测试ID、scaler/系数/概率/阈值保存。k14逐条概率、阈值、动作复现029 A/B/D。其仅有一集合/held，不能把零动作差称稳健。
5. **fallback。** 12次均为内层single_class，按原(R+1)/(N+2)常数处理，未删除或重抽。32,688指保存的内外模型状态，包含这些fallback，不等于32,688次两类Logistic优化。
6. **正式点和曲线。** 正式点完全训练内确定；D在自身正式risk处对A/B完整概率曲线＋正式点以及全非负global进行确定性/随机混合比较。所有测试阈值曲线只描述，不重选部署工作点。global未限λ≤2，GT知情包络不是可部署性能。
7. **不确定性。** 跨训练组合经验范围不是CI；bootstrap沿002患者cluster重抽，用同一seed权重对每轮固定预测计算，再跨唯一轮次平均。不在bootstrap内重训；实际重训变化由不同训练集合体现。患者身份、训练集合和OOF输出高度相关，不能把20轮当独立复制。
8. **稳定性。** 主动作不一致率按同一候选不同训练集合去重后计算。收尾额外由既有预测补出occurrence_and_unique_stability.csv，提供按不同完整轮次出现次数加权与去重两种描述，未改主结果。Spearman衡量排序相似性，概率与阈值波动分别记录，不主张因果。训练患者入选/未入选不是随机独立干预，尤其部分未入选组合仅1–3个。
9. **结论不能只看pooled。** k11合并对A/B平均+5.11/+3.83R，16/20同时为正；但025分别−1.37/−0.40R，026+2.00/+1.23R。k5来源变化时D动作变动大于A；026为主更保守、R保留77.05%，不是自动更优配比。不能据总体学习曲线断言扩大训练必然恢复迁移或确定最低11人。

## 收尾核验

closeout_001保存293,495项执行者检查：验证run全部文件hash；重算32,688个保存模型状态，0次新拟合；核对内外训练集合、训练scaler、内层OOF及80%阈值；核对每个测试单元、全队列映射、混淆矩阵、R/H/W和002指标；全部正式同风险比较用独立LP核验；逐候选去重动作变动率重算，bootstrap跨轮平均及区间由保存draw重建。

8项启动前合成测试保留，其中包括测试GT改变不影响拟合/阈值、最大规模计划去重、患者隔离及向量化bootstrap与逐次标量权重计算一致。收尾的close030.py只用于只读核验和聚合已有结果，不属于新方法，也不是独立审计。

## 安全复核入口

使用已有独立environment research-verifact-029。输出必须为不存在的新目录，禁止覆盖run_001/preparation_001；不要运行launch重复正式实验。

```powershell
E:/miniconda3/envs/research-verifact-029/python.exe -B tasks/030_gate_training_stability/close030.py outputs/030_gate_training_stability/audit_closeout_001
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -B -m unittest discover -s tasks/030_gate_training_stability -p test030.py -v
```

完整离线重训重放可用：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/030_gate_training_stability/run030.py --run-id audit_replay_001
```

该入口会重训全部固定集合、耗时较久；参数不变、无API。比较模型参数/阈值/预测/统计，时间、PID和运行路径等元信息例外。本次收尾使用保存状态重算，没有再次启动全部训练。

## 交付与停止

唯一主报告report.md。补充机器核验/逐患者均值/排序汇总/系数账本见closeout_001，全部原模型和统计见run_001。仅同步四份现行导航和当前状态，不回写历史报告/审计、冻结协议或run快照。当前数据不足以确定稳定最低训练人数或来源比例；不自动扩大材料、换特征/分类器、031或reserved40。后续独立审计由其他审计流程决定，不由执行者写PASS。
