"""After final verification, prepend current status while preserving line endings."""
from __future__ import annotations

from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"outputs/086_global_demonstration_selection"


def read(path):return json.loads(Path(path).read_text(encoding="utf-8"))


def prepend(path,line):
    raw=path.read_bytes()
    nl=b"\r\n" if b"\r\n" in raw else b"\n"
    first,sep,rest=raw.partition(nl)
    if not sep or not first.startswith(b"# ") or b"086\xe6\x9c\x80\xe6\x96\xb0" in raw:
        raise RuntimeError(f"Unsafe status insertion: {path}")
    path.write_bytes(first+nl+nl+line.encode("utf-8")+nl+nl+rest.lstrip(b"\r\n"))


def main():
    e=read(OUT/"E_analysis.json")
    v=read(OUT/"V_utility.json")
    cost=read(OUT/"cost_ledger.json")
    check=read(OUT/"selfcheck.json")
    if check["status"]!="PASS":raise RuntimeError("selfcheck not passed")
    star=e["D_star"]
    g=e["summaries"]["PriorG"]
    base=g["F4_new"];new=g[star+"_new"];control=g[e["nonutility_control"]+"_new"]
    short=(f"086固定四例全局效用选择完成：D/V/E为6/12/22患者，V36条五组实测选中{star}，"
        f"E110条同期F4/{star}/{e['nonutility_control']}＋Frozen PriorG正确"
        f"{base['correct']}/{new['correct']}/{control['correct']}、MCC"
        f"{base['MCC']:.4f}/{new['MCC']:.4f}/{control['MCC']:.4f}、错误支持"
        f"{base['false_S']}/{new['false_S']}/{control['false_S']}；"
        f"原价¥{cost['total_original_or_unknown_cny']:.6f}/30，"
        f"{cost['attempts']}次尝试，自检{check['checks']} PASS，独立审计未执行。"
        "085A已原位暂停，R1/AWS未部署或调用；默认B＋Frozen PriorG不变，084历史门槛不回写。"
        "用户接受小幅错误支持取舍但本轮三类风险仍单列。不用reserved、不改.gitignore，不自动下一任务。")
    entries={
        "AGENTS.md":f"**086最新（2026-09-26）：** {short}[086报告](outputs/086_global_demonstration_selection/report.md) · [085A暂停](tasks/085_r1_70b_model_swap/PAUSED_BY_USER.md)",
        "README.md":f"**086最新（2026-09-26）：** {short}[报告](outputs/086_global_demonstration_selection/report.md)",
        "docs/PROJECT_STATUS.md":f"**086最新（2026-09-26）：** {short}[报告](../outputs/086_global_demonstration_selection/report.md) · [085A暂停](../tasks/085_r1_70b_model_swap/PAUSED_BY_USER.md)",
        "docs/API_POLICY.md":f"**086专项结项（2026-09-26）：** 用户本条将附件内部¥20更新为本任务未优惠原价累计硬上限¥30；实际{cost['attempts']}次尝试、费用及未知预留¥{cost['total_original_or_unknown_cny']:.6f}/30。历史余额未结转，后续新任务默认¥20不变。[086账本](../outputs/086_global_demonstration_selection/cost_ledger.json)。",
        "docs/RESEARCH_EXECUTION.md":"**086更新（2026-09-26）：** 用户暂缓R1/AWS并交办全局固定四例效用选择；085A仅离线准备后原位暂停。086在D/V/E患者分离下只优化示例组、固定C48/T-S/Frozen PriorG，保留历史F4与同期对照。用户接受084观察到的小幅错误支持代价，不追溯改变084原门槛；NS/NA和false-S仍须报告，默认B不自动升级。[结果](../outputs/086_global_demonstration_selection/report.md)。",
        "docs/RUN_ENVIRONMENT.md":"**085A/086更新（2026-09-26）：** 085A的AWS adapter/tokenizer专用venv与缓存保留在被忽略的`.local_models`，状态为`PREDEPLOY_READY_PAUSED_BY_USER`；普通研究入口、`research-verifact-029`和阿里云Judge未切换到AWS。086通过现有`scripts/run_research.ps1`执行，只有任务独立`run086.py`是收费入口；不自动加载R1或访问AWS。[暂停记录](../tasks/085_r1_70b_model_swap/PAUSED_BY_USER.md)。",
    }
    for name,line in entries.items():prepend(ROOT/name,line)
    print("Updated status, policy and environment docs; existing line endings retained")


if __name__=="__main__":main()
