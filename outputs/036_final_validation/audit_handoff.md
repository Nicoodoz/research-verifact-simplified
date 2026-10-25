# 036 独立审计交接

状态：执行者完成；独立审计待进行。用户明确授权完成后直接提交/推送，不等待审计。不要把本文件或自检称独立PASS。

## 审查起点

提交前基准HEAD `ceda7443bb791a996b6aab66569a313cf69e0c52`；本轮代码与产物指纹在`handoff_manifest.json`，最终提交由Git定位本文件所在commit。报告和写作交接优先阅读，其次`tasks/036_final_validation/protocol.md`、三套freeze、development指标及R0/R1原始回执。

## 必查事项

1. 036用户授权reserved40及150元特殊上限；最终配置与参数、重复4人名单先于任何收费请求和GT连接。033撤回准备未继承；无reserved训练。
2. development补022 T/G/M/V是否沿原035折和参数定义；四折患者隔离；U4/Joint核对；035 MCC_T勘误是否准确。
3. Gate是否逐字复用033全40模型和原始12维score，Q缺失是否回退U0；所有概率后处理是否共享一次评分，温度是否保持标签。
4. 原API-BGE C48、原024模型0731/Qwen、body、token上限不变；请求不含GT/BHC/作者；B与scoring分清。
5. 全40/3573冻结覆盖及缺失ID、complete-case与总N敏感性；R1四人444条不作新增患者；不能静默筛成功样本。
6. 002指标、1000患者paired bootstrap；false-S与R/H/W、Gate的恢复H/阻止W/丢R是否区分；全标准方法和作者/患者/类别是否完整。
7. 所有回执SHA绑定、费用未知/在途预留、无重复HTTP200、总额105.576735≤150；原始费用非账单。
8. 报告不预设模块成功、不声称理论最优、NLL≠临床安全，原VeriFact对比不作单组件因果推断。自检与独立审计分清。

## 已做自检

7项单元测试，其中完整3675条旧推理数值锚点与370候选Gate原实现一致；发送前21项检查。最终安全重放62215项PASS，详见`verification_001.json`；含原回执、全部模型输出、002指标、主要bootstrap和错误转移恒等式。测试发现的common模块名冲突在reserved评价前修复，原/后指纹与失败说明在`evaluation_freeze_001/implementation_repair.json`。原历史源码未改。

费用导出的附加修正见`accounting_CURRENT.md`和`accounting_002/verification.json`：旧001金额完全正确，rerank token列因只看usage而漏掉meta字段；逐条复核4228份BGE回执补正，原001、费用与科研预测全部不变。Figure2在figures_002补入已评价的Vector scaling，以展示其NS召回代价；旧图及旧绘图源码保留。标签等价和444条跨轮同ID核对见`final_label_equivalence.csv`，MCC_T不纳入不变标签的泛化断言。

## 复查与禁止操作

使用`research-verifact-029`和项目启动器；安全入口见任务README。不要运行旧历史生成器；不要重新发送成功API、删除失败/未知记录、重新训练或用reserved调参。大文件仅gzip无损运输，本地原字节保留；恢复后hash一致，未改.gitignore。单元测试和安全复查0 API。

审计应独立形成`reviews/036_final_validation.md`，执行者未创建或代写独立审计结论。完成后停止，不自动实验。
