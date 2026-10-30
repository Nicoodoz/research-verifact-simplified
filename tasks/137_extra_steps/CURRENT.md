# 137 extra_steps：已启动原生续训

完整120 step369的权重、Adam、scheduler和RNG已在独立137目录恢复，目标固定518；新增149步/1192次呈现。当前进行首次反向检查／训练初始化，实际步数见实时进度；尚无新增分类结果。

32训练患者与20评价患者无交集，原GT、数据、顺序和loss不变。评价固定136的claim_repeat输入及160 ID，基线直接复用。

[方案](PROTOCOL.md) · [状态恢复回执](../../outputs/137_extra_steps/source_restore.json) · [实时进度](../../outputs/137_extra_steps/progress.md)
