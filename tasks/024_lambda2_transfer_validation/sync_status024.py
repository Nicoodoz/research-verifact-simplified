"""Update current navigation only; preserve historical reports and CRLF."""
from pathlib import Path
import common024 as c
def insert(path,text):
    raw=path.read_bytes();nl=b'\r\n' if b'\r\n' in raw else b'\n';pos=raw.index(nl)+len(nl)
    marker='**024当前'.encode()
    c.require(marker not in raw,'024 navigation already present')
    path.write_bytes(raw[:pos]+nl+text.replace('\n',nl.decode()).encode('utf-8')+nl+raw[pos:])
def run():
    insert(c.ROOT/'README.md','**024当前（2026-09-19）：** 固定λ=2跨后端/模型迁移已启动，用户授权相同重复JSON键无损折叠；续跑后出现不同值重复reason，按边界再次暂停。192个回答中191合法，3324逻辑请求未发；累计2.960295/80元，未评价性能、未用reserved40。[主报告](outputs/024_lambda2_transfer_validation/report.md) · [当前状态](outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。023“不自动启动024”为历史边界，本轮024由用户另行授权。\n')
    insert(c.ROOT/'docs/PROJECT_STATUS.md','**024当前（2026-09-19）：** 用户已授权实施024及性能评价前相同重复键无损修复。新出现不同值重复reason，按授权范围保留异常并暂停：194次尝试、192个回答、191合法；累计2.960295/80元（含未知预留0.129348），未计算效果。方法、prompt、证据与λ不变，未进入reserved40。[主报告](../outputs/024_lambda2_transfer_validation/report.md) · [状态](../outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。下方023不自动启动024的边界属于此前阶段。\n')
    insert(c.ROOT/'docs/REPRODUCIBILITY.md','**024当前离线入口：** `python tasks/024_lambda2_transfer_validation/verify024_repaired.py`，统一执行用户授权的相同重复值折叠并核对全部冻结请求/旧指纹。不同值重复reason仍异常，当前191/192合法、无全量性能结果；不要执行收费runner来做重放。见[024当前状态](../outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。\n')
    insert(c.TASK/'README.md','**024当前：** 用户已授权相同重复值无损折叠，使用format024.py；新冲突重复reason仍invalid，任务再次暂停。[最新状态](CURRENT_STATUS.md)。当前离线入口verify024_repaired.py，收费入口run024_streamed.py，分析入口analyze024_repaired.py。下方初版入口保留历史说明，不能绕过invalid状态续跑。\n')
if __name__=='__main__':run()
