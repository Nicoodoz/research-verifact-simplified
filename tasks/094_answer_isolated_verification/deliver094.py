"""Current navigation updates only; preserve prior task artifacts and user edits."""
import common094 as c
def replace(path,old,new):
    p=c.ROOT/path;b=p.read_bytes();nl='\r\n' if b'\r\n' in b else '\n';s=b.decode('utf-8');old=old.replace('\n',nl);new=new.replace('\n',nl);assert old in s,path;p.write_bytes(s.replace(old,new,1).encode('utf-8'))
def main():
    replace('AGENTS.md','093结项后','094结项后')
    replace('AGENTS.md','- 093已完成','- 094答案隔离式问答完成：冻结自然20/机制12，实际操作16/10；B/V/Q最终正确19/19/19及9/8/9，机制false-S 0/2/1。Q未超过B，唯一Q−V final救回涉及V引用无效，停止本版；费用¥2.508135/20，无重试，默认不变。不自动095。[094报告](outputs/094_answer_isolated_verification/report.md)。\n- 093已完成')
    replace('README.md','**093（2026-09-27）**','**094（2026-09-27）**')
    replace('README.md','F4、P90、R1替换和092模型均未升级默认。','F4、P90、R1替换、092模型及094候选均未升级默认。')
    replace('README.md','- [093报告与历史差异]','094完成固定C48下答案隔离式问答：自然20条B/V/Q最终均19正确，机制12条为9/8/9；机制Q的false-S为1，B为0。Q未证明系统增量，停止本版。157次HTTP200、0重试，原价¥2.508135/20；问题/来源核查和病例归因均留档。\n\n- [094正式报告](outputs/094_answer_isolated_verification/report.md)、[完整指标](outputs/094_answer_isolated_verification/detailed_tables.md)、[病例归因](outputs/094_answer_isolated_verification/case_analysis.md)\n- [093报告与历史差异]')
    replace('docs/PROJECT_STATUS.md','093完成）','094完成）')
    replace('docs/PROJECT_STATUS.md','当前研究已完成至093；本轮起始HEAD e3999daa6c','当前研究已完成至094；本轮起始HEAD 03a58bb3b')
    replace('docs/PROJECT_STATUS.md','|093固定预算补证|','|094答案隔离问答|固定C48、生成问题→可见V/隔离Q→同一Judge；自然20条B/V/Q正确19/19/19，机制12条9/8/9|实际操作26/32；Q未超过B，机制false-S由B0至Q1；停止本版，默认不变|\n|093固定预算补证|')
    replace('docs/PROJECT_STATUS.md','[093报告]','[094报告](../outputs/094_answer_isolated_verification/report.md) · [094历史区别](../outputs/094_answer_isolated_verification/history_difference.md) · [093报告]')
    replace('docs/PROJECT_STATUS.md','093用户允许现有全体患者研究；','094同样由用户授权使用既有全体材料，实际冻结自然20/机制12，不依赖旧模型对错；问题检查不读GT，GT仅用于登记分层及评价。没有全量新评价或新患者holdout。\n\n093用户允许现有全体患者研究；')
    replace('docs/PROJECT_STATUS.md','093新增API ¥4.097118/20','094新增API ¥2.508135/20，157个HTTP200、0重试、无GPU租赁，执行者自检通过、独立审计未执行。\n\n093新增API ¥4.097118/20')
    replace('docs/TASK_INDEX.md','截至093','截至094')
    replace('docs/TASK_INDEX.md','|---|---|---|---|','|---|---|---|---|\n|094_answer_isolated_verification|[正式报告](../outputs/094_answer_isolated_verification/report.md)|未执行；[执行者自检](../outputs/094_answer_isolated_verification/selfcheck.json)|B/V/Q首轮已完成，Q未证明优于B；停止本版，不自动095|')
    replace('docs/RESEARCH_EXECUTION.md','当前093已完成','当前094已完成')
    replace('docs/API_POLICY.md','092已完成，新增API为0；','094已完成，新增API按未优惠原价累计¥2.508135/20；092历史新增API仍为0。')
    replace('docs/API_POLICY.md','本次仅同步文档，未改客户端、密钥或.gitignore，未测试在线权限/余额。','各任务实际调用见其回执账本；094使用现行阿里云路由完成授权实验，未改密钥或.gitignore，未做余额探针。')
    c.put(c.OUT/'completion.json',dict(status='COMPLETE_STOP_VERSION',utc=c.now(),start_HEAD='03a58bb3ba19317b1d91700209cc5df7eae1b189',default_changed=False,independent_audit=False,API_cost_cny='2.508135',artifacts={p.relative_to(c.ROOT).as_posix():c.sha(p) for folder in [c.TASK,c.OUT] for p in folder.rglob('*') if p.is_file() and '__pycache__' not in str(p)}))
    print('Current navigation synchronized; completion hashes recorded')
if __name__=='__main__':main()
