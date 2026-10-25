"""Update only current navigation; preserve each existing file's encoding/newlines."""
from pathlib import Path
import common097 as c

def edit(rel,old,new):
    p=c.ROOT/rel;raw=p.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');s=raw.decode('utf-8-sig');crlf='\r\n' in s
    s=s.replace('\r\n','\n')
    assert s.count(old)==1,(rel,s.count(old))
    s=s.replace(old,new,1)
    if crlf:s=s.replace('\n','\r\n')
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+s.encode('utf-8'))

def main():
    edit('README.md',
        '当前已完成至 **096（2026-09-28）**，096已结项，不自动启动下一任务。',
        '当前已完成至 **097（2026-09-28）**，097已结项，不自动启动下一任务。')
    edit('README.md',
        '## 当前结论与入口\n\n',
        '## 当前结论与入口\n\n097完成同V4四臂原生接口对照：raw共同158条，C48 B/简洁任务/现行B＋G正确116/125/135；简洁任务只改善raw，未升级最终系统。40例源文核查显示405/482个检索片段被切开，但自动依赖构造及完整S0/W/F/H费用门槛未过，B无分类结果；新增492次HTTP200、¥12.967287/20，默认不变。[097报告](outputs/097_native_judge_source_dependence/report.md)。\n\n')
    edit('docs/PROJECT_STATUS.md',
        '# 项目现状（2026-09-28，096完成）\n\n当前研究已完成至096；096起始HEAD 28daf95e9b12270d8089246176023c66c4cf298e，实际HEAD以git为准。096已完成，不自动启动下一任务。',
        '# 项目现状（2026-09-28，097完成）\n\n当前研究已完成至097；097起始HEAD为71c183aab93cc947cbd99b2b8dd30ebfee251944，实际HEAD以git为准。097已完成，不自动启动下一任务。')
    edit('docs/PROJECT_STATUS.md',
        '## 最近结果与可主张范围\n\n',
        '## 最近结果与可主张范围\n\n097同V4四臂原生接口对照完成：raw共同158条C48 B/简洁任务/现行B＋G正确116/125/135；固定同body桥接12条raw改变4条。原生任务提供更强raw对照但没有最终系统升级。40例源文核查482条都可定位，405条切开父段；自动依赖和B完整四臂费用门槛未过，B无分类成绩。新增492 HTTP200、0重试、忙时原价¥12.967287/20，自检通过、独立审计未执行，默认不变。[正式报告](../outputs/097_native_judge_source_dependence/report.md)。\n\n')
    edit('docs/PROJECT_STATUS.md',
        '|096跨Judge/PriorG迁移|',
        '|097原生Judge/源文门槛|自然160冻结、raw共同158；40例源文离线核查；B无分类调用|C48简洁raw比B raw净+9，但比现行B＋G净−10；B构造/费用门槛未过，默认不变|\n|096跨Judge/PriorG迁移|')
    edit('docs/TASK_INDEX.md',
        '# 全部任务与当前入口（截至096结项）',
        '# 全部任务与当前入口（截至097结项）')
    edit('docs/TASK_INDEX.md',
        '|096_r1_native_priorg|',
        '|097_native_judge_source_dependence|[正式报告](../outputs/097_native_judge_source_dependence/report.md) · [同ID表](../outputs/097_native_judge_source_dependence/a_same_id.csv)|[执行者自检](../outputs/097_native_judge_source_dependence/selfcheck.json)，独立审计未执行|同V4原生接口raw有信号但未超过B＋G；B构造与费用门槛未过，默认不变|\n|096_r1_native_priorg|')
    edit('AGENTS.md',
        '# 项目工作约定（2026-09-28，096结项后）',
        '# 项目工作约定（2026-09-28，097结项后）')
    edit('AGENTS.md',
        '## 当前状态与数据授权\n\n',
        '## 当前状态与数据授权\n\n- 097已完成同V4四臂原生接口对照：自然160条，raw共同158条C48 B/原作者式简洁/现行B＋G正确116/125/135；原生raw较B净+9但最终不升级。12条同body桥接raw改变4条。40例源文核查显示482条可定位、405条切开父段；自动依赖构造与完整四臂费用门槛未过，B没有分类成绩。492 HTTP200、¥12.967287/20、0重试；自检通过、无独立审计，默认不变。[正式报告](outputs/097_native_judge_source_dependence/report.md)。\n')
    print('navigation 097 updated with preserved line endings')
if __name__=='__main__':main()
