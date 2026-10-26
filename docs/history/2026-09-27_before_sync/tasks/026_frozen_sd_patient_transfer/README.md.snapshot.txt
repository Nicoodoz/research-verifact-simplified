# 026 冻结SD跨患者组迁移

[发送前协议](../../outputs/026_frozen_sd_patient_transfer/protocol_001.md)。只在原024十患者训练最终SD，冻结后验证019六患者650条的新阿里云输出。固定λ2，Qwen只调用新D评分产生的候选，80元累计上限。

prepare026.py只准备/冻结；run026.py为真实收费入口，必须显式指定deepseek或qwen阶段。candidates026.py在D阶段结束后冻结不读GT的Qwen白名单。旧任务结果不覆盖，不自动reserved test。
