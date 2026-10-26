"""Replace current-state text while preserving each existing file's EOL/BOM."""
import common098 as c

def replace(rel, old, new):
    p=c.ROOT/rel;b=p.read_bytes();bom=b.startswith(b'\xef\xbb\xbf');text=b.decode('utf-8-sig');eol='\r\n' if b'\r\n' in b else '\n'
    text=text.replace('\r\n','\n')
    if old not in text:
        assert new in text,(rel,old);return
    assert text.count(old)==1,(rel,old)
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+text.replace(old,new).replace('\n',eol).encode('utf-8'))

def main():
    complete=(c.OUT/'complete.json').exists()
    if not complete:
        replace('README.md','研究实验已完成至 **097**；本页更新于 **2026-10-26**，没有自动开展下一项实验。',
                '研究实验已完成至 **097**；**098已于2026-10-26获用户正式授权并启动**，冻结方法与样本后按峰谷时段执行，结果尚未完成。[098协议](tasks/098_p90_native_confirmation/protocol.md)。')
        replace('docs/PROJECT_STATUS.md','当前研究已完成至097；097起始HEAD为71c183aab93cc947cbd99b2b8dd30ebfee251944，实际HEAD以git为准。097已完成，不自动启动下一任务。',
                '当前研究已完成至097；098已于2026-10-26获用户正式授权启动，新增API硬限50元。冻结自然400四臂、压力NS/NA各50条O/P、F80及四臂重复60；首批32次正式请求完成后等待闲时续跑，尚无完整分类结论。[098协议](../tasks/098_p90_native_confirmation/protocol.md) · [冻结与预算](../outputs/098_p90_native_confirmation/execution_freeze.json)。实际HEAD以git为准。')
        replace('AGENTS.md','- 研究完成至097；正式结果、费用与限制以[PROJECT_STATUS](docs/PROJECT_STATUS.md)和对应报告为准，不在规则文件重复维护整套数值。',
                '- 研究完成至097；098已获2026-10-26用户正式授权并启动，尚无完整结论。正式结果、费用与限制以[PROJECT_STATUS](docs/PROJECT_STATUS.md)和对应报告为准，不在规则文件重复维护整套数值。')
        p=c.ROOT/'docs/TASK_INDEX.md';old='|097_native_judge_source_dependence|';new='|098_p90_native_confirmation|[协议](../tasks/098_p90_native_confirmation/protocol.md) · [执行冻结](../outputs/098_p90_native_confirmation/execution_freeze.json)|尚未完成；独立审计未执行|用户已授权50元；自然400/压力100、F80、重复60，执行中，不按首批成绩扩量|\n|097_native_judge_source_dependence|'
        if '|098_p90_native_confirmation|' not in p.read_text(encoding='utf-8-sig'):replace('docs/TASK_INDEX.md',old,new)
    else:
        d=c.read(c.OUT/'decision.json');cost=c.read(c.OUT/'cost_ledger.json');a=c.read(c.OUT/'analysis.json')['panels']['natural']['tables']
        decision='支持继续冻结候选确认' if d['continue_candidate'] else '停止本版本，不扩大'
        summary=f"098已完成：自然400四臂、压力100条O/P、F80和四臂重复60；自然O/C/P/Q正确{'/'.join(str(a[m]['correct']) for m in ['O','C','P','Q'])}，{decision}，默认不变。新增API目录价及未知预留¥{cost['used_or_reserved_cny']:.6f}/50。执行者自检通过，独立审计未执行。[098报告](../outputs/098_p90_native_confirmation/report.md)。"
        replace('README.md','研究实验已完成至 **097**；**098已于2026-10-26获用户正式授权并启动**，冻结方法与样本后按峰谷时段执行，结果尚未完成。[098协议](tasks/098_p90_native_confirmation/protocol.md)。',
                f'研究实验已完成至 **098**（2026-10-26授权），{decision}，默认系统不变。[098报告](outputs/098_p90_native_confirmation/report.md)。')
        replace('docs/PROJECT_STATUS.md','当前研究已完成至097；098已于2026-10-26获用户正式授权启动，新增API硬限50元。冻结自然400四臂、压力NS/NA各50条O/P、F80及四臂重复60；首批32次正式请求完成后等待闲时续跑，尚无完整分类结论。[098协议](../tasks/098_p90_native_confirmation/protocol.md) · [冻结与预算](../outputs/098_p90_native_confirmation/execution_freeze.json)。实际HEAD以git为准。',summary+' 实际HEAD以git为准。')
        replace('AGENTS.md','- 研究完成至097；098已获2026-10-26用户正式授权并启动，尚无完整结论。正式结果、费用与限制以[PROJECT_STATUS](docs/PROJECT_STATUS.md)和对应报告为准，不在规则文件重复维护整套数值。',
                '- 研究完成至098；正式结果、费用与限制以[PROJECT_STATUS](docs/PROJECT_STATUS.md)和对应报告为准，不在规则文件重复维护整套数值。')
        replace('docs/TASK_INDEX.md','|098_p90_native_confirmation|[协议](../tasks/098_p90_native_confirmation/protocol.md) · [执行冻结](../outputs/098_p90_native_confirmation/execution_freeze.json)|尚未完成；独立审计未执行|用户已授权50元；自然400/压力100、F80、重复60，执行中，不按首批成绩扩量|',
                f'|098_p90_native_confirmation|[正式报告](../outputs/098_p90_native_confirmation/report.md) · [主表](../outputs/098_p90_native_confirmation/main_table.csv)|[执行者自检](../outputs/098_p90_native_confirmation/selfcheck.json)，独立审计未执行|{decision}；默认不变，不自动099|')
    print('Current navigation updated; historical reports unchanged')

if __name__=='__main__':main()
