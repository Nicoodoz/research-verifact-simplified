"""Current navigation only; no changes to historical019–023 conclusions or policies."""
import re
import core024 as c
def replace_line(path,prefix,text):
    data=path.read_bytes();s=data.decode('utf-8');nl='\r\n' if '\r\n' in s else '\n'
    pattern=re.escape(prefix)+r'[^\r\n]*'
    if re.search(pattern,s):s=re.sub(pattern,lambda _:text,s,count=1)
    else:
        pos=s.index(nl)+len(nl);s=s[:pos]+nl+text+nl+s[pos:]
    path.write_bytes(s.encode('utf-8'))
def run(complete=False):
    status='已按用户amendment_002统一核心字段规则续跑；解释字段异常及少量核心invalid不再阻断，全量请求正在完成。'
    if complete:
        a=c.OUT/'analysis_001';cost=c.read(a/'costs.json');decision=c.read(a/'decision.json')
        flags='；'.join(k+('方向支持' if v['direction_supported'] else '方向不支持') for k,v in decision.items())
        status=f"执行及评价完成，待独立审计。{flags}；{cost['valid_terminal']}/3516核心有效，费用及未知预留{cost['total_occupied_cny']:.6f}/80元。"
    for path,relative in [(c.ROOT/'README.md',''),(c.ROOT/'docs/PROJECT_STATUS.md','../'),(c.ROOT/'AGENTS.md','')]:
        replace_line(path,'**024当前',f'**024当前（2026-09-19）：** {status}固定λ=2、模型、prompt和API-BGE C48均未改，不使用reserved40。旧暂停及解析修订均保留。[主报告]({relative}outputs/024_lambda2_transfer_validation/report.md) · [状态]({relative}outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。023不自动启动024为此前边界，本次由用户另行授权；API路由和预算政策不变。')
    replace_line(c.ROOT/'docs/REPRODUCIBILITY.md','**024当前离线入口', '**024当前离线入口：** `python tasks/024_lambda2_transfer_validation/verify024_core.py`；完整指标重放使用 `analyze024_core.py --replay-dir outputs/replays/<new-directory>`（仅离线，新建目录）。当前采用用户amendment_002核心字段与各比较有效交集口径，旧strict/repaired入口仅用于历史核查。不要运行收费runner做重放。[当前状态](../outputs/024_lambda2_transfer_validation/CURRENT_STATUS.md)。')
    replace_line(c.TASK/'README.md','**024当前', '**024当前：** 用户amendment_002核心字段口径优先。解析core024.py，执行run024_direct.py（同一阿里云端点，本任务进程直连），评价analyze024_core.py，安全离线核查verify024_core.py。HTTP200包括核心invalid均不重跑。[最新状态](CURRENT_STATUS.md)。下方初版入口只代表历史阶段。')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--complete',action='store_true');a=p.parse_args();run(a.complete)
