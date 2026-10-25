"""Prepend completed 083 summary while preserving existing bytes and line endings."""
from pathlib import Path

blocks = {
    "AGENTS.md": ("# 项目背景", "**083最新（2026-09-26）：** 083原生理由增量验证完成：F4/B各1015份原生回答可回查，F4理由1015次固定Qwen抽取全部HTTP200；459条/14患者同监督训练，旧352＋新180共532条/22患者外评价。当前F4＋Frozen PriorG为447正确/MCC0.5703/错误支持21；分数＋raw监督N为451/0.5250/47；细结构R为443/0.4686/51，新180较F4＋G净−7、错误支持+15。R比N/G/T均少判对，错配理由负对照同为443；NS召回仅5.6%，不支持可迁移理由增量或系统升级。新增API未优惠原价¥0.620007/20，0新主Judge；自检22065 PASS、独立审计未执行。默认B＋G不变，停止本版、不用reserved、不改.gitignore、不commit/push、不自动084。[083报告](outputs/083_native_rationale_information/report.md)"),
    "README.md": ("# Research-VeriFact", "**083最新（2026-09-26）：** 原生F4理由459条/14患者同监督学习、旧352＋新180条/22患者外评价完成。F4＋Frozen PriorG为447正确/MCC0.5703/错误支持21，分数＋raw的N为451/0.5250/47，细结构R为443/0.4686/51。R较N/G/T均少判对；错配理由负对照与R同为443，新增180相对F4＋G净−7、错误支持+15。原生reason/checks覆盖1015/1015，新增Qwen提取1015次HTTP200、原价¥0.620007/20；自检22065 PASS、独立审计未执行。默认B＋G不变，停止当前理由抽取纠错版本；不用reserved、不改.gitignore、不commit/push、不自动084。[083报告](outputs/083_native_rationale_information/report.md)"),
    "docs/PROJECT_STATUS.md": ("# 项目现状总览", "**083最新（2026-09-26）：** 459条/14患者F4同监督训练，旧352＋新180条/22患者外评价完成。F4＋Frozen PriorG、分数＋raw监督N、原生理由细结构R正确447/451/443，MCC0.5703/0.5250/0.4686，错误支持21/47/51。R比同数据N/C/G/T均无净增量，错配理由负对照同为443；新180较F4＋G净−7且错误支持+15，NS召回严重下降。1015份原生理由均可回查；1015次新Qwen HTTP200，原价¥0.620007/20，0新主Judge；自检22065 PASS、独立审计未执行。默认B＋G不变，停止本版，不用reserved、不自动084、不提交推送。[083报告](../outputs/083_native_rationale_information/report.md)"),
}

for filename, (heading, update) in blocks.items():
    path = Path(filename)
    raw = path.read_bytes()
    sep = b"\r\n" if b"\r\n" in raw else b"\n"
    prefix = heading.encode("utf-8") + sep + sep
    assert raw.startswith(prefix) and "**083最新".encode("utf-8") not in raw
    path.write_bytes(prefix + update.encode("utf-8") + sep + sep + raw[len(prefix):])
    assert path.read_bytes().endswith(raw[len(prefix):])
    print(filename, "preserved", "CRLF" if sep == b"\r\n" else "LF")
