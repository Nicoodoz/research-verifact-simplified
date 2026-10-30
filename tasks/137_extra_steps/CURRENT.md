# 137 extra_steps：完整续训准备就绪

固定120 step369→518、追加149步/1192次呈现。源Adam含496个状态槽、均为step369，scheduler和RNG可读取；32训练患者与20评价患者无交集。原GT、数据、顺序和loss不变。

使用与136完全相同的claim_repeat输入及160 ID；基线136已全1817完成，直接复用。尚未执行新训练，CPU检查不代表分类收益。

[方案](PROTOCOL.md) · [准备摘要](../../outputs/137_extra_steps/preparation.json) · [实时进度](../../outputs/137_extra_steps/progress.md)
