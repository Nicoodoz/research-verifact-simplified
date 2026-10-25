# 收尾索引路径修复记录

首次finalize033在构建统一排名CSV时将“非030模型”误认为“一定新保存在033/models”，遇到直接复用031的A原16全训练模型时FileNotFoundError。保存修改前源码finalize_before.py，原handoff目录尚空；尚未修改导航、报告或任何科学结果。

修复仅将模型定位改为search_001/model_usage.json内已冻结的实际source path。两个031复用模型不是新拟合；36个新定向拟合数及所有排名/选择/预测/统计保持。没有新训练或参数变化。
