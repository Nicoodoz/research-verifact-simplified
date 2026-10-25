"""One-time 084 status insertion preserving each existing file's line endings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
entries = {
    "AGENTS.md": "**084最新（2026-09-26）：** 083冻结OOF零API补表确认NS类别塌缩在训练折外已有预警。全仓库原C48扩覆盖后，084新增180条/21患者同期B/F4＋Frozen PriorG正确155/161、MCC0.5881/0.6433、错误支持6/30→8/30；净+6但错误支持率+6.67百分点，超过事前3点容忍，患者区间跨0。历史532与新队列方向相同，合并712仅描述。071选例训练患者池与084有121条/14人重叠，池外59条/7人；均已暴露development。360次HTTP200、原价¥12.166821/20、0重试；执行者自检6043 PASS，独立审计未执行。默认B＋G不变，F4仅保留有代价的开发候选；不使用reserved、不改.gitignore、不commit/push、不自动085。[084报告](outputs/084_f4_coverage_validation/report.md)",
    "README.md": "**084最新（2026-09-26）：** 083冻结OOF零API诊断确认NS塌缩在训练侧已可见。084全仓库C48扩覆盖新增180条/21患者，固定B/F4＋Frozen PriorG正确155/161，MCC0.5881/0.6433，错误支持6/30→8/30。净+6但非S错误支持率+6.67百分点，超过事前3点容忍，患者区间跨0；默认B＋G不变，F4仅作有代价的开发候选。071选例训练患者池与新队列121条/14人重叠，池外59条/7人，全部仍是暴露development。360次HTTP200、原价¥12.166821/20、0重试；自检6043 PASS、独立审计未执行。不用reserved、不改.gitignore、不commit/push、不自动085。[084报告](outputs/084_f4_coverage_validation/report.md)",
    "docs/PROJECT_STATUS.md": "**084最新（2026-09-26）：** 083冻结OOF零API诊断显示NS类别塌缩在训练折外已有预警。084从全仓库原C48覆盖扩展，在180条/21患者同期B/F4上，Frozen PriorG正确155/161、MCC0.5881/0.6433、错误支持6/30→8/30；净+6、ΔMCC+0.0552，但错误支持率+6.67百分点超过事前3点容忍，患者区间跨0。071选例训练患者池重叠121条/14人，池外59条/7人；仍为暴露development。360次HTTP200、原价¥12.166821/20，自检6043 PASS、独立审计未执行。默认B＋G不变，F4仅保留有代价候选；不使用reserved、不自动085、不提交推送。[084报告](../outputs/084_f4_coverage_validation/report.md)",
    "docs/API_POLICY.md": "**084专项结项（2026-09-26）：** 用户授权全任务未优惠原价硬上限¥20；固定阿里云北京`deepseek-v4-flash-0731`新增360次HTTP200、0重试/未知，按峰时输入¥3/输出¥9每百万token累计¥12.166821/20。原价账目见[084费用台账](../outputs/084_f4_coverage_validation/cost_ledger.json)。本专项不改变后续新任务默认¥20或任何历史预算，不因优惠扩大额度。",
}

for rel, sentence in entries.items():
    path = ROOT / rel
    raw = path.read_bytes()
    if b"**084" in raw:
        raise RuntimeError(f"084 status already inserted: {rel}")
    newline = b"\r\n" if b"\r\n" in raw else b"\n"
    assert raw.count(b"\n") == raw.count(b"\r\n") if newline == b"\r\n" else b"\r\n" not in raw
    marker = newline + newline
    at = raw.index(marker) + len(marker)
    inserted = sentence.encode("utf-8") + marker
    path.write_bytes(raw[:at] + inserted + raw[at:])
    print(rel, "inserted", len(inserted), "bytes")
