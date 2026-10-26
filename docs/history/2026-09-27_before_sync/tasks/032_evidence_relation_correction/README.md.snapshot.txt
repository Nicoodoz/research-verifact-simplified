# 032：证据关系增强的三分类纠错

用户授权执行的新实验；不是继续调031的repeat/trace Gate。
目标为提高完整三分类PA/MCC，false-S作为重要代价报告。

## 环境与入口
离线克隆旧GPU conda环境失败（历史包未缓存）；实际使用任务专用venv：
`.local_models/032/venv`，开启system-site-packages，只读复用现有research GPU库。
主research-verifact、research-verifact-029及research的包均未修改。
运行时通过conda research设置正确DLL路径，再调用任务venv解释器：

```powershell
Set-Location D:\Research-VeriFact
E:\miniconda3\Scripts\conda.exe run --no-capture-output -n research D:\Research-VeriFact\.local_models\032\venv\Scripts\python.exe -u tasks\032_evidence_relation_correction\run032.py --resume
```

`--resume`只继续没有完成标记的阶段，不覆盖旧结果。不同时启动两个runner。
只下载公开模型时运行download032.py；推理与训练均断网，不调用收费API。

## 设置
28名训练患者/2527条，12名已暴露确认患者/1148条，完全沿031名单；reserved40不使用。
冻结DeBERTa NLI、两粒度C48证据实例、小型注意力聚合及残差三分类。
普通评分纠错、固定聚合、单粒度、去lambda、仅旧候选应用范围均作对照。
超参仅28训练患者内部四折选择；确认标签在最终盲预测保存后连接。

## 产物
`outputs/032_evidence_relation_correction/`：准备/协议、模型来源、NLI绑定、训练选择、盲预测、完整评价、报告和交审。
公开预训练权重和可重建配对缓存留在`.local_models/032`，不进Git。
执行者自检不等于独立审计；不自动提交、推送或启动033。
