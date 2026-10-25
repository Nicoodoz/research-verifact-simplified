"""Insert the 082 final status while preserving existing bytes and line endings."""
from pathlib import Path

blocks = {
    "AGENTS.md": ("# 项目背景", "**082最新（2026-09-26）：** 082标注锚点驱动配置适配完成：14患者各302条配对R/E校准视图，旧352＋新180共532条/22患者外评价。当前B＋Frozen PriorG、F4＋Frozen PriorG、F4标准独立校准、训练选中的F4共享＋配置修正分别正确438/447/436/453，MCC 0.5481/0.5703/0.5457/0.5622，错误支持18/21/18/33。修正在新180相对F4＋G净0且错误支持+7，三族训练风险门槛均失败；边界富集独立校准回到G逐例同标签，未证明额外方法价值。1070次新HTTP200，未优惠原价¥35.281902/50；24条/22患者同体重复、执行者自检3750 PASS，独立审计未执行。默认B＋G不变，停止本版三类评分适配，不用reserved、不改.gitignore、不commit/push、不自动083。[082报告](outputs/082_anchor_configuration_adaptation/report.md)"),
    "README.md": ("# Research-VeriFact", "**082最新（2026-09-26）：** 完成14患者302条配对锚点的代表性／等规模边界覆盖比较，旧352＋新180共532条/22患者外评价。B＋Frozen PriorG、F4＋Frozen PriorG、F4独立校准、F4共享＋配置修正正确438/447/436/453，MCC 0.5481/0.5703/0.5457/0.5622，错误支持18/21/18/33。配置修正训练风险门槛失败，在新180相对F4＋G净正确0、错误支持+7；边界覆盖独立校准只回到G。未优惠原价¥35.281902/50，1070次新HTTP200；24条同体重复、自检3750 PASS，独立审计未执行。默认B＋G不变，停止本版评分适配；不用reserved、不改.gitignore、不commit/push、不自动083。[082报告](outputs/082_anchor_configuration_adaptation/report.md)"),
    "docs/PROJECT_STATUS.md": ("# 项目现状总览", "**082最新（2026-09-26）：** 14患者R/E各302条配对锚点、22患者旧352＋新180条同ID评价完成。当前B＋G、F4＋G、F4同数据独立校准、F4共享＋配置修正正确438/447/436/453，MCC 0.5481/0.5703/0.5457/0.5622，错误支持18/21/18/33。训练风险约束全失败，修正在新180相对F4＋G净0且错误支持+7；边界富集标准校准逐例与G相同。原价¥35.281902/50、1070新HTTP200，24条同体重复，执行者自检3750 PASS、独立审计未执行。当前默认B＋G不变，停止本版三类评分适配，不自动083、不提交推送。[082报告](../outputs/082_anchor_configuration_adaptation/report.md)"),
}

for filename, (heading, update) in blocks.items():
    path = Path(filename)
    raw = path.read_bytes()
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    prefix = heading.encode("utf-8") + newline + newline
    assert raw.startswith(prefix), filename
    assert b"**082\xe6\x9c\x80\xe6\x96\xb0" not in raw, filename
    path.write_bytes(prefix + update.encode("utf-8") + newline + newline + raw[len(prefix):])
    final = path.read_bytes()
    assert final[len(prefix) + len(update.encode("utf-8")) + len(newline) * 2:] == raw[len(prefix):]
    assert final.count(newline) == raw.count(newline) + 2
    print(filename, "preserved", "CRLF" if newline == b"\r\n" else "LF")
