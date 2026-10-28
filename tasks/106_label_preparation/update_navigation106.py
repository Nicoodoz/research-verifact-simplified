"""Update current navigation only, preserving original UTF-8 BOM and line endings."""
import common106 as c
import difflib

SUMMARY=('106研究、数据与CPU实现准备完成，停在READY_FOR_NEXT_GPU_DECISION。'
         '推荐同104原196条的label_mean对全局归一label_sum最小目标诊断；'
         '只规划新训sum，原105标签适配器作控制，本轮没有GPU/AutoDL或目标模型训练。'
         '3675训练池及两个512匹配候选已备，53条选型诊断、16条筛选分歧和3对训练邻居已审读；'
         '新输入缺口对称隔离，原GT/reference与105结果保留。API新增0/10元，默认不变，不自动启动或推送。')


def edit(relative, function):
    path=c.ROOT/relative;data=path.read_bytes();bom=data.startswith(b'\xef\xbb\xbf')
    text=data.decode('utf-8-sig')
    # Preserve every unchanged physical line, including mixed historical endings.
    original=text.splitlines(keepends=True)
    old=[line.rstrip('\r\n') for line in original]
    normalized=function(text.replace('\r\n','\n'))
    new=normalized.splitlines()
    crlf=data.count(b'\r\n');bare_lf=data.count(b'\n')-crlf
    newline='\r\n' if crlf>bare_lf else '\n'
    result=[]
    for kind,i,j,a,b in difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes():
        if kind=='equal':
            result.extend(original[i:j])
        elif kind in ('replace','insert'):
            for index,line in enumerate(new[a:b],start=a):
                ending=newline if index<len(new)-1 or normalized.endswith('\n') else ''
                result.append(line+ending)
    payload=''.join(result).encode('utf-8')
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+payload)


def intro(text, prefix):
    start=text.index('105完整执行与离线分析完成')
    end=text.index('\n\n',start)
    return text[:start]+SUMMARY+f' [106一页决定]({prefix}outputs/106_label_preparation/decision.md) · [106报告]({prefix}outputs/106_label_preparation/report.md) · [105最终报告]({prefix}outputs/105_brief_supervision/final_report.md)。'+text[end:]


def main():
    edit('README.md',lambda t:intro(t,''))
    def agents(t):
        t=intro(t,'')
        marker='## 当前状态与数据授权\n\n'
        return t.replace(marker,marker+'- 106仅研究/数据/CPU准备完成，最终推荐同196标签目标最小诊断；API专项10元实际0。训练40人可准备全3675池，选型20人仅解释已有结果，确认40人本轮不读取选方法；GPU与下一任务须新决定。\n',1)
    edit('AGENTS.md',agents)
    def status(t):
        t=intro(t,'../').replace('# 项目现状（2026-10-28，105完整执行与负结果分析完成）','# 项目现状（2026-10-28，106准备完成，待GPU决策）',1)
        marker='|---|---|---|\n'
        row='|106标签目标准备|3675池、两个512匹配候选、53+16源文审读、同196归一sum入口及CPU验证|READY_FOR_NEXT_GPU_DECISION；推荐先诊断标签目标，0新API/GPU，不自动启动|\n'
        return t.replace(marker,marker+row,1)
    edit('docs/PROJECT_STATUS.md',status)
    def principles(t):
        t=intro(t,'../').replace('# 研究设计与执行原则（2026-10-26）','# 研究设计与执行原则（2026-10-28）',1)
        old='105本轮已经完成；用户要求手动关机且现已确认。仅保存与离线分析、双仓库发布已获授权，没有启动下一任务、重训或默认升级授权。102封存、103/104历史结论保留。'
        new='105已完成且用户确认关机，不恢复实例。用户另已明确授权106的研究、训练患者数据准备和CPU实现，收费API专项上限10元且实际0；本轮不授权GPU或目标模型训练。106准备完成后仍须下一次GPU明确决定，默认系统及102—105历史结论保留。'
        assert old in t
        return t.replace(old,new,1)
    edit('docs/RESEARCH_EXECUTION.md',principles)
    def index(t):
        t=t.replace('（105完整执行与最终分析；2026-10-28）','（106准备完成，待GPU决策；2026-10-28）',1)
        marker='|---|---|---|---|\n'
        row='|106_label_preparation|[一页决定](../outputs/106_label_preparation/decision.md) · [报告](../outputs/106_label_preparation/report.md) · [协议](../tasks/106_label_preparation/protocol.md) · [交接](../tasks/106_label_preparation/GPU_HANDOFF.md)|[执行者自检](../outputs/106_label_preparation/final_selfcheck.json)；[子代理反证复核](../outputs/106_label_preparation/adversarial_review.md)，非医生审计|仅研究/数据/CPU准备；推荐同196标签mean/sum诊断，0新增API/GPU，READY_FOR_NEXT_GPU_DECISION|\n'
        return t.replace(marker,marker+row,1)
    edit('docs/TASK_INDEX.md',index)
    def environment(t):
        marker='\n\n'
        pos=t.index(marker)+len(marker)
        line=('106未启动GPU。CPU统计/评价继续使用research-verifact-029；该环境缺torch与tokenizers，未安装或升级。'
              '仅tokenizer/Jinja编码及小CPU张量验证使用既有research激活加032 venv，未加载9B或初始化CUDA；'
              '本地tokenizers0.22.0与未来105冻结环境0.23.3不同，开卡前必须逐条重新核token SHA。'
              '当前交接只含9B必要代码、受限输入与mean控制适配器，不包含基础权重、凭据或27B/35B材料。\n\n')
        return t[:pos]+line+t[pos:]
    edit('docs/RUN_ENVIRONMENT.md',environment)
    c.write(c.TASK/'CURRENT.md','# 106当前入口：准备完成，待GPU决策\n\n'+SUMMARY+'\n\n'
        '唯一推荐：同原196的label_mean与全局归一label_sum。sum从原9B新训2轮/50步，mean复用冻结105控制；缓存条件不符需新决定，不自动开卡。\n\n'
        '[一页决定](../../outputs/106_label_preparation/decision.md) · [完整报告](../../outputs/106_label_preparation/report.md) · [冻结协议](protocol.md) · [GPU交接](GPU_HANDOFF.md) · [自检](../../outputs/106_label_preparation/final_selfcheck.json)。\n\n'
        '私有包及临床原文/控制适配器不可发布。用户已确认当前Codex服务条件，必要源文审读完成；没有向web或额外API发送临床原文。本轮API实际0元，GPU0，不提交或推送。')
    print(c.canonical(dict(navigation_updated=True,old_experiment_reports_not_modified=True)))


if __name__=='__main__':main()
